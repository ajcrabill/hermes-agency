# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
prototype DB — persistent iteration tracking.

Tables:
  prototypes      one row per "thing we're prototyping" (a newsletter
                  draft, a pitch email, a workbook chapter, etc.)
  prototype_rounds   the iteration ledger — each round records the
                  draft text + the feedback received + a summary of
                  what changed in the next round

Used by skills via the helpers in `prototype-from-example` and any
Writing skill that wants to track its convergence.

Diagnostic question this makes possible: "we've iterated 6 times on
this newsletter — are we converging?" Answered by looking at the
change_summary deltas across rounds.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


PROTOTYPE_DB_DEFAULT = STATE_DIR / "prototypes.db"
SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prototypes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    profile             TEXT NOT NULL,                 -- which agent's prototype this is
    audience            TEXT NOT NULL DEFAULT '',
    purpose             TEXT NOT NULL DEFAULT '',
    example_sources     TEXT NOT NULL DEFAULT '[]',    -- JSON array of source identifiers
    style_signature     TEXT NOT NULL DEFAULT '{}',    -- JSON serialization of StyleSignature
    status              TEXT NOT NULL DEFAULT 'active', -- active | shipped | abandoned
    current_round       INTEGER NOT NULL DEFAULT 0,
    metadata            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prototypes_profile ON prototypes(profile);
CREATE INDEX IF NOT EXISTS idx_prototypes_status  ON prototypes(status);

CREATE TABLE IF NOT EXISTS prototype_rounds (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prototype_id        INTEGER NOT NULL REFERENCES prototypes(id),
    round_number        INTEGER NOT NULL,
    draft_text          TEXT NOT NULL DEFAULT '',
    draft_path          TEXT NOT NULL DEFAULT '',
    feedback            TEXT NOT NULL DEFAULT '',
    change_summary      TEXT NOT NULL DEFAULT '',
    feedback_source     TEXT NOT NULL DEFAULT 'owner',  -- owner | kb | analyst | self
    metadata            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    UNIQUE(prototype_id, round_number)
);
CREATE INDEX IF NOT EXISTS idx_rounds_proto ON prototype_rounds(prototype_id, round_number);
"""


@dataclass
class PrototypeRound:
    id: int
    prototype_id: int
    round_number: int
    draft_text: str
    draft_path: str
    feedback: str
    change_summary: str
    feedback_source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


def init_prototype_db(path: Path | None = None) -> Path:
    target = path or PROTOTYPE_DB_DEFAULT
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
    init_prototype_db(path)
    c = sqlite3.connect(str(path or PROTOTYPE_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Public API ──────────────────────────────────────────────────────────


def start_prototype(
    *,
    name: str,
    profile: str,
    audience: str = "",
    purpose: str = "",
    example_sources: list[str] | None = None,
    style_signature: dict | None = None,
    initial_draft: str = "",
    initial_draft_path: str = "",
    metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Create a new prototype + record round 0 (the first draft).
    Returns the prototype id."""
    now = _now()
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO prototypes (name, profile, audience, purpose,
                                     example_sources, style_signature,
                                     current_round, metadata,
                                     created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (name, profile, audience, purpose,
             json.dumps(example_sources or []),
             json.dumps(style_signature or {}),
             json.dumps(metadata or {}), now, now),
        )
        prototype_id = int(cur.lastrowid)
        db.execute(
            """
            INSERT INTO prototype_rounds (prototype_id, round_number, draft_text,
                                            draft_path, feedback, change_summary,
                                            feedback_source, created_at)
            VALUES (?, 0, ?, ?, '', 'initial prototype', 'self', ?)
            """,
            (prototype_id, initial_draft, initial_draft_path, now),
        )
        db.commit()
        return prototype_id
    finally:
        db.close()


def record_iteration(
    prototype_id: int,
    *,
    draft_text: str = "",
    draft_path: str = "",
    feedback: str = "",
    change_summary: str = "",
    feedback_source: str = "owner",
    metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Record the next round. Returns the round_number assigned."""
    now = _now()
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT current_round FROM prototypes WHERE id=?", (prototype_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"prototype {prototype_id} not found")
        next_round = int(row["current_round"]) + 1
        db.execute(
            """
            INSERT INTO prototype_rounds (prototype_id, round_number, draft_text,
                                            draft_path, feedback, change_summary,
                                            feedback_source, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (prototype_id, next_round, draft_text, draft_path,
             feedback, change_summary, feedback_source,
             json.dumps(metadata or {}), now),
        )
        db.execute(
            "UPDATE prototypes SET current_round=?, updated_at=? WHERE id=?",
            (next_round, now, prototype_id),
        )
        db.commit()
        return next_round
    finally:
        db.close()


def get_prototype(prototype_id: int, db_path: Path | None = None) -> dict | None:
    """Full prototype + all rounds (ordered)."""
    db = _conn(db_path)
    try:
        proto_row = db.execute(
            "SELECT * FROM prototypes WHERE id=?", (prototype_id,),
        ).fetchone()
        if not proto_row:
            return None
        proto = dict(proto_row)
        proto["example_sources"] = json.loads(proto.get("example_sources") or "[]")
        proto["style_signature"] = json.loads(proto.get("style_signature") or "{}")
        proto["metadata"] = json.loads(proto.get("metadata") or "{}")
        rounds = db.execute(
            "SELECT * FROM prototype_rounds WHERE prototype_id=? ORDER BY round_number",
            (prototype_id,),
        ).fetchall()
        proto["rounds"] = [_row_to_round(r) for r in rounds]
        return proto
    finally:
        db.close()


def list_prototypes(
    *, profile: str | None = None, status: str = "active",
    db_path: Path | None = None,
) -> list[dict]:
    db = _conn(db_path)
    try:
        if profile:
            rows = db.execute(
                "SELECT * FROM prototypes WHERE profile=? AND status=? "
                "ORDER BY updated_at DESC",
                (profile, status),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM prototypes WHERE status=? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["example_sources"] = json.loads(d.get("example_sources") or "[]")
            out.append(d)
        return out
    finally:
        db.close()


def mark_shipped(prototype_id: int, db_path: Path | None = None) -> None:
    db = _conn(db_path)
    try:
        db.execute(
            "UPDATE prototypes SET status='shipped', updated_at=? WHERE id=?",
            (_now(), prototype_id),
        )
        db.commit()
    finally:
        db.close()


# ── Diagnostic: "are we converging?" ─────────────────────────────────────


def convergence_diagnostic(prototype_id: int, db_path: Path | None = None) -> dict:
    """Look at the round history and produce a convergence sketch.

    Returns:
      {
        "round_count": int,
        "feedback_lengths": [...],
        "is_likely_stuck": bool,
        "reason": str,
      }

    Heuristics:
      - 5+ rounds without `mark_shipped` → likely stuck
      - Feedback length not decreasing over recent rounds → likely
        stuck (operator is still finding lots to say)
      - Same feedback_source on every round → only one viewpoint;
        consider involving another reviewer (KB / Analyst)
    """
    proto = get_prototype(prototype_id, db_path=db_path)
    if not proto:
        return {"error": "prototype not found"}
    rounds = proto["rounds"]
    if not rounds:
        return {"round_count": 0, "is_likely_stuck": False, "reason": "no rounds"}

    fb_lengths = [len(r.feedback) for r in rounds if r.feedback]
    sources = [r.feedback_source for r in rounds]
    reasons: list[str] = []

    if len(rounds) >= 5 and proto.get("status") == "active":
        reasons.append(f"{len(rounds)} rounds without shipping")

    if len(fb_lengths) >= 3:
        recent = fb_lengths[-3:]
        if recent[-1] >= recent[0]:
            reasons.append("recent feedback not shorter — convergence unclear")

    distinct_sources = set(sources)
    if len(distinct_sources) == 1 and len(rounds) >= 3 and "self" not in distinct_sources:
        reasons.append(f"only one reviewer ({next(iter(distinct_sources))}) — consider adding a second viewpoint")

    return {
        "round_count": len(rounds),
        "feedback_lengths": fb_lengths,
        "is_likely_stuck": len(reasons) >= 2,
        "reason": "; ".join(reasons) if reasons else "converging or too early to tell",
    }


# ── Helpers ─────────────────────────────────────────────────────────────


def _row_to_round(r: sqlite3.Row) -> PrototypeRound:
    return PrototypeRound(
        id=int(r["id"]),
        prototype_id=int(r["prototype_id"]),
        round_number=int(r["round_number"]),
        draft_text=str(r["draft_text"]),
        draft_path=str(r["draft_path"]),
        feedback=str(r["feedback"]),
        change_summary=str(r["change_summary"]),
        feedback_source=str(r["feedback_source"]),
        metadata=json.loads(r["metadata"] or "{}"),
        created_at=str(r["created_at"]),
    )


__all__ = [
    "PROTOTYPE_DB_DEFAULT",
    "init_prototype_db",
    "start_prototype",
    "record_iteration",
    "get_prototype",
    "list_prototypes",
    "mark_shipped",
    "convergence_diagnostic",
    "PrototypeRound",
]
