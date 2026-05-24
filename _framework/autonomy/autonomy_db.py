# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
autonomy.db — schema for skill autonomy state + history.

Tables:
  - skill_autonomy           current state per skill (level, consecutive_clean)
  - skill_autonomy_history   event log (every clean_run, fail, promote, demote)

History is append-only. Current state is derived from the most recent
relevant event. Promotion/demotion decisions write a new history row
AND update the current-state row in the same transaction.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import AUTONOMY_DB

SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_autonomy (
    skill                    TEXT NOT NULL,
    profile                  TEXT NOT NULL,
    level                    INTEGER NOT NULL DEFAULT 1,
    consecutive_clean        INTEGER NOT NULL DEFAULT 0,
    last_event_ts            TEXT,
    last_event_kind          TEXT,
    PRIMARY KEY (skill, profile)
);

CREATE TABLE IF NOT EXISTS skill_autonomy_history (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                       TEXT NOT NULL,
    skill                    TEXT NOT NULL,
    profile                  TEXT NOT NULL,
    kind                     TEXT NOT NULL,    -- clean_run | failure | promote | demote
                                                --        | audit_blocked_promote | learning_blocked_promote
                                                --        | manual_set
    from_level               INTEGER,
    to_level                 INTEGER,
    reason                   TEXT,
    payload                  TEXT              -- JSON
);

CREATE INDEX IF NOT EXISTS idx_sah_skill ON skill_autonomy_history(skill, profile, ts);
CREATE INDEX IF NOT EXISTS idx_sah_kind  ON skill_autonomy_history(kind, ts);
"""


def init_autonomy_db(path: Path | None = None) -> Path:
    target = path or AUTONOMY_DB
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
        else:
            stored = int(row[0])
            if stored > SCHEMA_VERSION:
                raise RuntimeError(
                    f"autonomy.db schema_version={stored} is newer than framework supports ({SCHEMA_VERSION})."
                )
        conn.commit()
    finally:
        conn.close()
    return target


def _conn(path: Path | None = None) -> sqlite3.Connection:
    target = path or AUTONOMY_DB
    init_autonomy_db(target)
    c = sqlite3.connect(str(target))
    c.row_factory = sqlite3.Row
    return c


def get_skill_level(skill: str, profile: str, db_path: Path | None = None) -> int:
    """Return the current level for a (skill, profile). Defaults to L1 if absent."""
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT level FROM skill_autonomy WHERE skill=? AND profile=?",
            (skill, profile),
        ).fetchone()
        return int(row["level"]) if row else 1
    finally:
        db.close()


def set_skill_level(skill: str, profile: str, level: int, db_path: Path | None = None, reason: str = "manual") -> None:
    """Manually set the level (operator override). Records a history row."""
    if not (1 <= level <= 5):
        raise ValueError(f"level must be 1-5, got {level}")
    now = datetime.now(timezone.utc).isoformat()
    db = _conn(db_path)
    try:
        prev = db.execute(
            "SELECT level FROM skill_autonomy WHERE skill=? AND profile=?",
            (skill, profile),
        ).fetchone()
        prev_level = int(prev["level"]) if prev else 1
        db.execute(
            "INSERT OR REPLACE INTO skill_autonomy(skill, profile, level, consecutive_clean, last_event_ts, last_event_kind) "
            "VALUES (?, ?, ?, 0, ?, 'manual_set')",
            (skill, profile, level, now),
        )
        db.execute(
            "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason) "
            "VALUES (?, ?, ?, 'manual_set', ?, ?, ?)",
            (now, skill, profile, prev_level, level, reason),
        )
        db.commit()
    finally:
        db.close()


def get_action_class_min_level(action_class: str) -> int:
    """Look up the L1-L5 minimum for an action class from invariants.yaml."""
    from _framework.manifest import load_invariants

    inv = load_invariants()
    for ac in inv.get("action_classes", []):
        if ac["id"] == action_class:
            return int(ac["min_level"])
    raise ValueError(f"unknown action class: {action_class}")


__all__ = [
    "SCHEMA_VERSION",
    "init_autonomy_db",
    "get_skill_level",
    "set_skill_level",
    "get_action_class_min_level",
]
