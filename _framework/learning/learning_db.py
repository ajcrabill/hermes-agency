# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
learning.db — schema + connection management.

Single SQLite file at `$AGENCY_HOME/_state/learning.db`. Three tables:

- `learning_rules`  the corrections, with embeddings + tag arrays
- `firings`         every recorded use of a rule
- `recapture_events` detected duplicate-correction events

Schema versioning lives in `meta` table. Migrations are forward-only;
each one bumps `schema_version` by 1. The framework refuses to start
against a future schema (operator must upgrade framework, not
downgrade DB).

This module is intentionally low-level: no business logic, no rule
resolution, no embedding. Other learning/ modules use it.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from _framework.constants import LEARNING_DB, STATE_DIR

SCHEMA_VERSION = 1

# ── Schema ───────────────────────────────────────────────────────────────


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_rules (
    id              TEXT PRIMARY KEY,
    correction      TEXT NOT NULL,
    source          TEXT NOT NULL,
    skill_tags      TEXT NOT NULL,        -- JSON array of skill tags + optional 'general'
    role_tags       TEXT,                 -- JSON array: chief-of-staff, analyst-judge, etc.
    voice_tags      TEXT,                 -- JSON array: firm, warm-not-flattering, we-not-i
    is_hard         INTEGER NOT NULL DEFAULT 0,    -- 1 = deterministically checkable
    status          TEXT NOT NULL DEFAULT 'active', -- active | suspended | superseded
    replaced_by     TEXT,
    embedding       BLOB,                  -- numpy-serialized vector or NULL
    embedding_model TEXT,                  -- deployment-picked embedding identifier
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_lr_status ON learning_rules(status);
CREATE INDEX IF NOT EXISTS idx_lr_skill ON learning_rules(skill_tags);
CREATE INDEX IF NOT EXISTS idx_lr_created ON learning_rules(created_at);

CREATE TABLE IF NOT EXISTS firings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id         TEXT NOT NULL REFERENCES learning_rules(id) ON DELETE CASCADE,
    skill_tag       TEXT NOT NULL,
    profile         TEXT NOT NULL,
    was_overridden  INTEGER NOT NULL DEFAULT 0,   -- 1 = agent tried to violate a hard rule
    action_summary  TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fr_rule ON firings(rule_id, created_at);
CREATE INDEX IF NOT EXISTS idx_fr_skill ON firings(skill_tag, created_at);
CREATE INDEX IF NOT EXISTS idx_fr_profile ON firings(profile, created_at);

CREATE TABLE IF NOT EXISTS recapture_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    new_rule_id     TEXT NOT NULL REFERENCES learning_rules(id) ON DELETE CASCADE,
    similar_to      TEXT NOT NULL REFERENCES learning_rules(id) ON DELETE CASCADE,
    similarity      REAL NOT NULL,
    skill_tags      TEXT NOT NULL,
    detected_at     TEXT NOT NULL,
    notified        INTEGER NOT NULL DEFAULT 0,
    dismissed       INTEGER NOT NULL DEFAULT 0,  -- owner marked as "not-recapture"
    dismissal_note  TEXT
);

CREATE INDEX IF NOT EXISTS idx_re_new ON recapture_events(new_rule_id);
CREATE INDEX IF NOT EXISTS idx_re_when ON recapture_events(detected_at);
CREATE INDEX IF NOT EXISTS idx_re_open ON recapture_events(dismissed, detected_at);

-- denylist for recapture detection: if owner has said "rule X and rule Y
-- are NOT duplicates," we record that here so the detector excludes the
-- pair from future alerts. Avoids the same correction-similarity pair
-- firing forever.
CREATE TABLE IF NOT EXISTS recapture_denylist (
    rule_a          TEXT NOT NULL,
    rule_b          TEXT NOT NULL,
    added_at        TEXT NOT NULL,
    note            TEXT,
    PRIMARY KEY (rule_a, rule_b)
);
"""


# ── Connection ───────────────────────────────────────────────────────────


def _conn(path: Path | None = None) -> sqlite3.Connection:
    target = path or LEARNING_DB
    target.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(target))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def get_db(path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to learning.db, ensuring schema exists."""
    init_learning_db(path=path)
    return _conn(path)


def init_learning_db(path: Path | None = None) -> Path:
    """Create the database + schema if absent. Idempotent. Returns DB path."""
    target = path or LEARNING_DB
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(SCHEMA_V1)
        # Record / upgrade schema_version
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
                    f"learning.db schema_version={stored} is newer than framework supports ({SCHEMA_VERSION}). "
                    "Upgrade hermes-agency before opening this deployment."
                )
            # forward migrations would run here (none yet)
        conn.commit()
    finally:
        conn.close()
    return target


# ── Helpers for JSON-column round-trips ─────────────────────────────────


def encode_json_col(value: list[str] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(list(value))


def decode_json_col(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
        return list(decoded) if isinstance(decoded, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def row_to_rule(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a learning_rules row to a friendly dict (JSON cols decoded)."""
    d = dict(row)
    d["skill_tags"] = decode_json_col(d.get("skill_tags"))
    d["role_tags"] = decode_json_col(d.get("role_tags"))
    d["voice_tags"] = decode_json_col(d.get("voice_tags"))
    return d


__all__ = [
    "SCHEMA_VERSION",
    "get_db",
    "init_learning_db",
    "encode_json_col",
    "decode_json_col",
    "row_to_rule",
]
