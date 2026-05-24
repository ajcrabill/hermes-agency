# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
CRM SQLite schema + CRUD.

Tables:
  contacts          one person, with primary + alternate emails
  leads             one organization or opportunity, with status
  sent_threads      Gmail-thread → lead mapping for outbound
  reply_log         inbound replies with sentiment + lead attribution

The schema is intentionally generic. Domain-specific fields (NCES
ids, district types, podcast genres, etc.) live in the JSON
`metadata` columns rather than as typed columns. This keeps the
framework reusable across very different agencies.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


CRM_DB_DEFAULT = STATE_DIR / "crm.db"
SCHEMA_VERSION = 1


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL UNIQUE,
    alternate_emails   TEXT NOT NULL DEFAULT '[]',   -- JSON array
    lead_id            INTEGER REFERENCES leads(id),
    role               TEXT,                          -- free-form (e.g. "primary", "decision-maker")
    metadata           TEXT NOT NULL DEFAULT '{}',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contacts_lead ON contacts(lead_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email_domain ON contacts(email);

CREATE TABLE IF NOT EXISTS leads (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,                 -- org / opportunity name
    primary_email      TEXT,
    secondary_email    TEXT,
    status             TEXT NOT NULL DEFAULT 'new',   -- new | potential | active | doc-provided | no-interest | neutral | converted | dormant
    last_touch_primary    TEXT,
    last_touch_secondary  TEXT,
    source             TEXT,                          -- where this lead came from
    metadata           TEXT NOT NULL DEFAULT '{}',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_primary_email ON leads(primary_email);

CREATE TABLE IF NOT EXISTS sent_threads (
    thread_id          TEXT PRIMARY KEY,              -- Gmail thread id
    lead_id            INTEGER REFERENCES leads(id),
    contact_id         INTEGER REFERENCES contacts(id),
    message_id         TEXT,                          -- last sent message id in thread
    sent_at            TEXT NOT NULL,
    body_hash          TEXT,
    subject            TEXT,
    metadata           TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_sent_threads_lead ON sent_threads(lead_id);

CREATE TABLE IF NOT EXISTS reply_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id          TEXT,                          -- Gmail thread (may be null if no thread match)
    lead_id            INTEGER REFERENCES leads(id),
    contact_id         INTEGER REFERENCES contacts(id),
    from_email         TEXT NOT NULL,
    from_name          TEXT,
    subject            TEXT,
    snippet            TEXT,
    sentiment          TEXT,                          -- positive | negative | neutral | question | unknown
    requested_doc      TEXT,                          -- if the reply asked for something specific
    match_priority     INTEGER,                       -- 1-4: thread/email/domain/unmatched
    replied_at         TEXT NOT NULL,
    metadata           TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_reply_log_lead ON reply_log(lead_id, replied_at);
CREATE INDEX IF NOT EXISTS idx_reply_log_thread ON reply_log(thread_id);
"""


def init_crm_db(path: Path | None = None) -> Path:
    target = path or CRM_DB_DEFAULT
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(SCHEMA_V1)
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
        conn.commit()
    finally:
        conn.close()
    return target


def _conn(path: Path | None = None) -> sqlite3.Connection:
    init_crm_db(path)
    c = sqlite3.connect(str(path or CRM_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Contacts ────────────────────────────────────────────────────────────


def add_contact(
    *, name: str, email: str, alternate_emails: list[str] | None = None,
    lead_id: int | None = None, role: str | None = None,
    metadata: dict | None = None, db_path: Path | None = None,
) -> int:
    """Insert a contact. If the email exists, return existing id."""
    now = _now()
    db = _conn(db_path)
    try:
        existing = db.execute("SELECT id FROM contacts WHERE email=?", (email,)).fetchone()
        if existing:
            return int(existing["id"])
        cur = db.execute(
            """
            INSERT INTO contacts (name, email, alternate_emails, lead_id, role, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, email, json.dumps(alternate_emails or []),
                lead_id, role or "", json.dumps(metadata or {}),
                now, now,
            ),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def update_contact(contact_id: int, **fields) -> None:
    """Patch a contact's fields. Pass any subset of the contact columns."""
    if not fields:
        return
    now = _now()
    setters = ["updated_at=?"]
    params: list[Any] = [now]
    for k, v in fields.items():
        if k in ("alternate_emails", "metadata") and not isinstance(v, str):
            v = json.dumps(v)
        setters.append(f"{k}=?")
        params.append(v)
    params.append(contact_id)
    db = _conn()
    try:
        db.execute(f"UPDATE contacts SET {', '.join(setters)} WHERE id=?", params)
        db.commit()
    finally:
        db.close()


def find_contact(contact_id: int, db_path: Path | None = None) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def find_contact_by_email(email: str, db_path: Path | None = None) -> dict | None:
    """Match primary email OR any alternate email."""
    db = _conn(db_path)
    try:
        # Primary
        row = db.execute("SELECT * FROM contacts WHERE email=?", (email,)).fetchone()
        if row:
            return dict(row)
        # Alternates (JSON contains check via LIKE — coarse but adequate for v0.3)
        rows = db.execute(
            "SELECT * FROM contacts WHERE alternate_emails LIKE ?",
            (f'%"{email}"%',),
        ).fetchall()
        for r in rows:
            try:
                alts = json.loads(r["alternate_emails"])
                if email in alts:
                    return dict(r)
            except json.JSONDecodeError:
                continue
        return None
    finally:
        db.close()


# ── Leads ───────────────────────────────────────────────────────────────


def add_lead(
    *, name: str, primary_email: str | None = None,
    secondary_email: str | None = None, status: str = "new",
    source: str | None = None, metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    now = _now()
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO leads (name, primary_email, secondary_email, status, source, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, primary_email, secondary_email, status,
             source or "", json.dumps(metadata or {}),
             now, now),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def update_lead(lead_id: int, **fields) -> None:
    if not fields:
        return
    now = _now()
    setters = ["updated_at=?"]
    params: list[Any] = [now]
    for k, v in fields.items():
        if k == "metadata" and not isinstance(v, str):
            v = json.dumps(v)
        setters.append(f"{k}=?")
        params.append(v)
    params.append(lead_id)
    db = _conn()
    try:
        db.execute(f"UPDATE leads SET {', '.join(setters)} WHERE id=?", params)
        db.commit()
    finally:
        db.close()


def list_leads(
    *, status: str | None = None, limit: int = 100,
    db_path: Path | None = None,
) -> list[dict]:
    db = _conn(db_path)
    try:
        if status:
            rows = db.execute(
                "SELECT * FROM leads WHERE status=? ORDER BY updated_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM leads ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def find_lead_by_domain(email: str, db_path: Path | None = None) -> list[dict]:
    """Find all leads where the sender's email domain matches the
    domain of any contact tied to the lead, or of the lead's
    primary/secondary email."""
    if "@" not in email:
        return []
    domain = email.split("@", 1)[1].lower()
    pattern = f"%@{domain}"
    db = _conn(db_path)
    try:
        rows = db.execute(
            """
            SELECT DISTINCT l.* FROM leads l
            LEFT JOIN contacts c ON c.lead_id = l.id
            WHERE LOWER(l.primary_email) LIKE ?
               OR LOWER(l.secondary_email) LIKE ?
               OR LOWER(c.email) LIKE ?
            """,
            (pattern, pattern, pattern),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Sent threads ────────────────────────────────────────────────────────


def log_sent_thread(
    *, thread_id: str, lead_id: int | None = None,
    contact_id: int | None = None, message_id: str | None = None,
    body_hash: str | None = None, subject: str | None = None,
    metadata: dict | None = None, db_path: Path | None = None,
) -> None:
    db = _conn(db_path)
    try:
        db.execute(
            """
            INSERT OR REPLACE INTO sent_threads
            (thread_id, lead_id, contact_id, message_id, sent_at, body_hash, subject, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (thread_id, lead_id, contact_id, message_id, _now(),
             body_hash or "", subject or "", json.dumps(metadata or {})),
        )
        db.commit()
    finally:
        db.close()


def find_sent_thread(thread_id: str, db_path: Path | None = None) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT * FROM sent_threads WHERE thread_id=?", (thread_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


# ── Reply log ───────────────────────────────────────────────────────────


def log_reply(
    *, from_email: str, replied_at: str | None = None,
    thread_id: str | None = None, lead_id: int | None = None,
    contact_id: int | None = None, from_name: str | None = None,
    subject: str | None = None, snippet: str | None = None,
    sentiment: str | None = None, requested_doc: str | None = None,
    match_priority: int = 4, metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Log an inbound reply. `match_priority` is the 1-4 from the
    reply-matcher (1=thread, 2=email, 3=domain, 4=unmatched)."""
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO reply_log
            (thread_id, lead_id, contact_id, from_email, from_name, subject,
             snippet, sentiment, requested_doc, match_priority, replied_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (thread_id, lead_id, contact_id, from_email, from_name or "",
             subject or "", snippet or "", sentiment or "unknown",
             requested_doc or "", match_priority,
             replied_at or _now(),
             json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def find_recent_replies(
    *, lead_id: int | None = None, days: int = 90,
    db_path: Path | None = None,
) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = _conn(db_path)
    try:
        if lead_id is not None:
            rows = db.execute(
                "SELECT * FROM reply_log WHERE lead_id=? AND replied_at >= ? "
                "ORDER BY replied_at DESC",
                (lead_id, cutoff),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM reply_log WHERE replied_at >= ? ORDER BY replied_at DESC",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


__all__ = [
    "CRM_DB_DEFAULT",
    "init_crm_db",
    "add_contact", "update_contact", "find_contact", "find_contact_by_email",
    "add_lead", "update_lead", "list_leads", "find_lead_by_domain",
    "log_sent_thread", "find_sent_thread",
    "log_reply", "find_recent_replies",
]
