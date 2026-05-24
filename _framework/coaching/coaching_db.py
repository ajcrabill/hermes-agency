# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
coaching.db — schema + CRUD for the structured coaching workflow.

Generalized from v7's book_coaching.db. Renamed "books" → "projects"
so the substrate works for thesis writing, screenplays, white papers,
or any other long-form coached creative work — not just books.

Tables:
  users            email is the human-readable id (PK is autoinc, but
                   email is enforced UNIQUE — matches how the inbox
                   polling identifies authors)
  projects         one per book/thesis/etc.; tracks phase + cadence
  phases           per-phase status + deliverable file pointer
  qa_history       every Q + A pair; answer_source = voice|typed|imported
  deliverables     outputs per phase (drafts, outlines, etc.)
  ingested_files   attachment dedup by sha256 + char count

The schema is operator-extensible via JSON `metadata` columns where
applicable.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR

COACHING_DB_DEFAULT = STATE_DIR / "coaching.db"
SCHEMA_VERSION = 1


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL DEFAULT '',
    metadata        TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    title               TEXT NOT NULL,
    project_type        TEXT NOT NULL DEFAULT 'book',     -- book | thesis | screenplay | white-paper | workbook | other
    methodology         TEXT NOT NULL DEFAULT 'default',  -- operator-named methodology
    short_name          TEXT,                              -- kebab slug for paths
    status              TEXT NOT NULL DEFAULT 'active',   -- active | paused | completed | archived
    phase               INTEGER NOT NULL DEFAULT 1,       -- current phase number
    questions_per_cycle INTEGER NOT NULL DEFAULT 3,
    question_depth      TEXT NOT NULL DEFAULT 'medium',   -- easy | medium | hard
    support_level       TEXT NOT NULL DEFAULT 'normal',   -- max | normal | minimal
    continuous_mode     INTEGER NOT NULL DEFAULT 0,       -- 0 = time-based cadence; 1 = submission-driven
    current_section     TEXT NOT NULL DEFAULT '',         -- generalizes v7's "current_chapter"
    last_cycle_at       TEXT,                              -- last time we sent questions
    last_response_at    TEXT,
    paused_until        TEXT,
    metadata            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

CREATE TABLE IF NOT EXISTS phases (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(id),
    phase_number        INTEGER NOT NULL,
    name                TEXT,                             -- methodology-defined (Discovery / Outline / etc.)
    status              TEXT NOT NULL DEFAULT 'pending',  -- pending | active | completed
    deliverable_file    TEXT NOT NULL DEFAULT '',
    started_at          TEXT,
    completed_at        TEXT,
    created_at          TEXT NOT NULL,
    UNIQUE(project_id, phase_number)
);
CREATE INDEX IF NOT EXISTS idx_phases_project ON phases(project_id);

CREATE TABLE IF NOT EXISTS qa_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(id),
    phase_number        INTEGER NOT NULL,
    question            TEXT NOT NULL,
    answer              TEXT NOT NULL DEFAULT '',
    answer_source       TEXT NOT NULL DEFAULT 'typed',    -- voice | typed | imported
    depth               TEXT NOT NULL DEFAULT 'medium',
    question_cycle      INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    answered_at         TEXT,
    metadata            TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_qa_project ON qa_history(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_qa_open ON qa_history(project_id, answered_at);

CREATE TABLE IF NOT EXISTS deliverables (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(id),
    phase_number        INTEGER NOT NULL,
    name                TEXT NOT NULL,
    file_path           TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'draft',    -- draft | reviewed | final
    version             INTEGER NOT NULL DEFAULT 1,
    metadata            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deliverables_project ON deliverables(project_id);

CREATE TABLE IF NOT EXISTS ingested_files (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER REFERENCES projects(id),
    filename            TEXT NOT NULL,
    sha256              TEXT NOT NULL UNIQUE,
    chars               INTEGER NOT NULL DEFAULT 0,
    source_msg_id       TEXT,
    extracted_path      TEXT,                              -- where the extracted text was stored
    ingested_at         TEXT NOT NULL,
    metadata            TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ingested_project ON ingested_files(project_id);
"""


def init_coaching_db(path: Path | None = None) -> Path:
    target = path or COACHING_DB_DEFAULT
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
    init_coaching_db(path)
    c = sqlite3.connect(str(path or COACHING_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Users ───────────────────────────────────────────────────────────────


def add_user(*, email: str, name: str = "", metadata: dict | None = None,
             db_path: Path | None = None) -> int:
    """Upsert by email. Returns user id."""
    now = _now()
    db = _conn(db_path)
    try:
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return int(existing["id"])
        cur = db.execute(
            "INSERT INTO users (email, name, metadata, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (email, name, json.dumps(metadata or {}), now, now),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def find_user_by_email(email: str, db_path: Path | None = None) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


# ── Projects ────────────────────────────────────────────────────────────


def add_project(
    *, user_id: int, title: str, project_type: str = "book",
    methodology: str = "default", short_name: str | None = None,
    phase: int = 1, questions_per_cycle: int = 3,
    question_depth: str = "medium", metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Create a new project for a user. Returns project id."""
    now = _now()
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO projects (
                user_id, title, project_type, methodology, short_name,
                phase, questions_per_cycle, question_depth,
                metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, project_type, methodology, short_name or "",
             phase, questions_per_cycle, question_depth,
             json.dumps(metadata or {}), now, now),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def find_project(project_id: int, db_path: Path | None = None) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def list_active_projects(db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT * FROM projects WHERE status='active' "
            "AND (paused_until IS NULL OR paused_until < ?) "
            "ORDER BY updated_at DESC",
            (_now(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def advance_phase(project_id: int, *, to_phase: int | None = None,
                  db_path: Path | None = None) -> int:
    """Move the project to the next phase (or a specific phase).
    Marks the prior phase as completed; returns the new phase number."""
    now = _now()
    db = _conn(db_path)
    try:
        row = db.execute("SELECT phase FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise ValueError(f"project {project_id} not found")
        prior = int(row["phase"])
        new_phase = to_phase if to_phase is not None else prior + 1
        # Mark prior phase completed
        db.execute(
            "UPDATE phases SET status='completed', completed_at=? "
            "WHERE project_id=? AND phase_number=?",
            (now, project_id, prior),
        )
        # Insert new phase row if absent
        db.execute(
            "INSERT OR IGNORE INTO phases (project_id, phase_number, status, created_at) "
            "VALUES (?, ?, 'active', ?)",
            (project_id, new_phase, now),
        )
        db.execute(
            "UPDATE phases SET status='active', started_at=? "
            "WHERE project_id=? AND phase_number=? AND started_at IS NULL",
            (now, project_id, new_phase),
        )
        db.execute(
            "UPDATE projects SET phase=?, updated_at=? WHERE id=?",
            (new_phase, now, project_id),
        )
        db.commit()
        return new_phase
    finally:
        db.close()


# ── Q&A history ─────────────────────────────────────────────────────────


def record_qa(
    *, project_id: int, phase_number: int, question: str,
    answer: str = "", answer_source: str = "typed",
    depth: str = "medium", question_cycle: int = 0,
    metadata: dict | None = None, db_path: Path | None = None,
) -> int:
    """Record a Q (and optionally A if already answered). Returns row id."""
    if answer_source not in ("voice", "typed", "imported"):
        answer_source = "typed"
    now = _now()
    answered_at = now if answer else None
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO qa_history (
                project_id, phase_number, question, answer, answer_source,
                depth, question_cycle, created_at, answered_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, phase_number, question, answer, answer_source,
             depth, question_cycle, now, answered_at,
             json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def get_open_questions(
    project_id: int, phase_number: int | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Questions without an answered_at."""
    db = _conn(db_path)
    try:
        if phase_number is not None:
            rows = db.execute(
                "SELECT * FROM qa_history WHERE project_id=? AND phase_number=? "
                "AND answered_at IS NULL ORDER BY created_at",
                (project_id, phase_number),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM qa_history WHERE project_id=? AND answered_at IS NULL "
                "ORDER BY created_at",
                (project_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_qa_history(
    project_id: int, phase_number: int | None = None,
    limit: int = 200, db_path: Path | None = None,
) -> list[dict]:
    db = _conn(db_path)
    try:
        if phase_number is not None:
            rows = db.execute(
                "SELECT * FROM qa_history WHERE project_id=? AND phase_number=? "
                "ORDER BY created_at DESC LIMIT ?",
                (project_id, phase_number, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM qa_history WHERE project_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def answer_question(
    qa_id: int, answer: str, *, answer_source: str = "typed",
    db_path: Path | None = None,
) -> None:
    """Mark a previously-asked question as answered."""
    if answer_source not in ("voice", "typed", "imported"):
        answer_source = "typed"
    now = _now()
    db = _conn(db_path)
    try:
        db.execute(
            "UPDATE qa_history SET answer=?, answer_source=?, answered_at=? WHERE id=?",
            (answer, answer_source, now, qa_id),
        )
        db.commit()
    finally:
        db.close()


# ── Deliverables ────────────────────────────────────────────────────────


def log_deliverable(
    *, project_id: int, phase_number: int, name: str,
    file_path: str = "", status: str = "draft",
    version: int = 1, metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    now = _now()
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO deliverables (project_id, phase_number, name, file_path,
                                       status, version, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, phase_number, name, file_path, status, version,
             json.dumps(metadata or {}), now, now),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def list_deliverables(project_id: int, db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT * FROM deliverables WHERE project_id=? ORDER BY phase_number, version",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Ingested files (dedup by sha256) ────────────────────────────────────


def log_ingested_file(
    *, sha256: str, filename: str, chars: int = 0,
    project_id: int | None = None, source_msg_id: str | None = None,
    extracted_path: str | None = None, metadata: dict | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Idempotent log of an ingested file. Returns the row id on insert,
    or None if the sha256 was already present (dedup hit)."""
    db = _conn(db_path)
    try:
        existing = db.execute(
            "SELECT id FROM ingested_files WHERE sha256=?", (sha256,),
        ).fetchone()
        if existing:
            return None
        cur = db.execute(
            """
            INSERT INTO ingested_files (project_id, filename, sha256, chars,
                                         source_msg_id, extracted_path,
                                         ingested_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, filename, sha256, chars,
             source_msg_id or "", extracted_path or "",
             _now(), json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def find_ingested_file(sha256: str, db_path: Path | None = None) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute("SELECT * FROM ingested_files WHERE sha256=?", (sha256,)).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


__all__ = [
    "COACHING_DB_DEFAULT", "SCHEMA_VERSION",
    "init_coaching_db",
    "add_user", "find_user_by_email",
    "add_project", "find_project", "list_active_projects", "advance_phase",
    "record_qa", "get_open_questions", "get_qa_history", "answer_question",
    "log_deliverable", "list_deliverables",
    "log_ingested_file", "find_ingested_file",
]
