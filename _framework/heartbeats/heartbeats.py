# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
heartbeats.db — append-only liveness log with cadence-aware staleness.

Schema:
  CREATE TABLE heartbeats (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      component       TEXT NOT NULL,
      ts              TEXT NOT NULL,
      payload         TEXT
  );
  CREATE TABLE heartbeat_summary (
      component       TEXT PRIMARY KEY,
      last_success_at TEXT NOT NULL,
      total_count     INTEGER NOT NULL DEFAULT 0
  );

`heartbeats` keeps history (auto-pruned by maintenance); `heartbeat_summary`
gives O(1) "is component X alive?" lookups for the dashboard +
Sentinel's heartbeat-watch.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _framework.constants import HEARTBEATS_DB

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS heartbeats (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    component TEXT NOT NULL,
    ts        TEXT NOT NULL,
    payload   TEXT
);
CREATE INDEX IF NOT EXISTS idx_hb_component_ts ON heartbeats(component, ts);

CREATE TABLE IF NOT EXISTS heartbeat_summary (
    component       TEXT PRIMARY KEY,
    last_success_at TEXT NOT NULL,
    total_count     INTEGER NOT NULL DEFAULT 0
);
"""

SCHEMA_VERSION = 1


def init_heartbeats_db(path: Path | None = None) -> Path:
    target = path or HEARTBEATS_DB
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
    init_heartbeats_db(path)
    c = sqlite3.connect(str(path or HEARTBEATS_DB))
    c.row_factory = sqlite3.Row
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def beat(component: str, db_path: Path | None = None) -> None:
    """The minimal heartbeat — just record that this component succeeded."""
    if not component:
        raise ValueError("component required")
    now = _now()
    db = _conn(db_path)
    try:
        db.execute("INSERT INTO heartbeats (component, ts) VALUES (?, ?)", (component, now))
        db.execute(
            """
            INSERT INTO heartbeat_summary (component, last_success_at, total_count)
            VALUES (?, ?, 1)
            ON CONFLICT(component) DO UPDATE SET
                last_success_at = excluded.last_success_at,
                total_count = total_count + 1
            """,
            (component, now),
        )
        db.commit()
    finally:
        db.close()


def beat_with_payload(component: str, payload: dict, db_path: Path | None = None) -> None:
    """Heartbeat with a small JSON payload (e.g. items processed, last task id)."""
    if not component:
        raise ValueError("component required")
    now = _now()
    db = _conn(db_path)
    try:
        db.execute(
            "INSERT INTO heartbeats (component, ts, payload) VALUES (?, ?, ?)",
            (component, now, json.dumps(payload)),
        )
        db.execute(
            """
            INSERT INTO heartbeat_summary (component, last_success_at, total_count)
            VALUES (?, ?, 1)
            ON CONFLICT(component) DO UPDATE SET
                last_success_at = excluded.last_success_at,
                total_count = total_count + 1
            """,
            (component, now),
        )
        db.commit()
    finally:
        db.close()


def last_beat(component: str, db_path: Path | None = None) -> str | None:
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT last_success_at FROM heartbeat_summary WHERE component=?",
            (component,),
        ).fetchone()
        return row["last_success_at"] if row else None
    finally:
        db.close()


def recent(component: str | None = None, limit: int = 100, db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        if component:
            rows = db.execute(
                "SELECT * FROM heartbeats WHERE component=? ORDER BY ts DESC LIMIT ?",
                (component, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM heartbeats ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def stale_components(db_path: Path | None = None) -> list[dict]:
    """Compute staleness against invariants.yaml::expected_intervals_seconds.
    Returns components past 2× their expected interval."""
    from _framework.manifest import load_invariants

    inv = load_invariants()
    expected = inv.get("expected_intervals_seconds", {})

    now = datetime.now(timezone.utc)
    db = _conn(db_path)
    try:
        rows = db.execute("SELECT * FROM heartbeat_summary").fetchall()
    finally:
        db.close()

    out = []
    for r in rows:
        comp = r["component"]
        last = r["last_success_at"]
        if not last:
            continue
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            continue
        age_sec = (now - last_dt).total_seconds()
        expected_sec = expected.get(comp, 300)   # default 5 minutes
        if age_sec > expected_sec * 2:
            out.append({
                "component": comp,
                "last_success_at": last,
                "age_seconds": int(age_sec),
                "expected_seconds": int(expected_sec),
            })
    return out


__all__ = [
    "init_heartbeats_db",
    "beat",
    "beat_with_payload",
    "last_beat",
    "recent",
    "stale_components",
]
