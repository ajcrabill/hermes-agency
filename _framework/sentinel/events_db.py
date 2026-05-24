# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
events.db — Sentinel's append-only event log.

Single table. Every notable thing in the agency lands here as one row.
This is the trend-queryable surface for "what worked / what didn't"
analyses.

Writers: any subsystem can `append(...)` events. Sentinel is the
primary reader. The dashboard plugin tails this for the live events
feed.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _framework.constants import EVENTS_DB

SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    kind     TEXT NOT NULL,
    actor    TEXT,
    target   TEXT,
    severity TEXT,
    payload  TEXT
);

CREATE INDEX IF NOT EXISTS idx_ev_ts    ON events(ts);
CREATE INDEX IF NOT EXISTS idx_ev_kind  ON events(kind, ts);
CREATE INDEX IF NOT EXISTS idx_ev_actor ON events(actor, ts);

CREATE TABLE IF NOT EXISTS events_hourly (
    bucket_ts        TEXT NOT NULL,          -- ISO hour boundary
    kind             TEXT NOT NULL,
    severity         TEXT,
    count            INTEGER NOT NULL,
    PRIMARY KEY (bucket_ts, kind, severity)
);
"""


def init_events_db(path: Path | None = None) -> Path:
    target = path or EVENTS_DB
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
                    f"events.db schema_version={stored} newer than framework supports ({SCHEMA_VERSION})."
                )
        conn.commit()
    finally:
        conn.close()
    return target


def _conn(path: Path | None = None) -> sqlite3.Connection:
    init_events_db(path)
    c = sqlite3.connect(str(path or EVENTS_DB))
    c.row_factory = sqlite3.Row
    return c


# ── Public surface ───────────────────────────────────────────────────────


def append(
    kind: str,
    actor: str | None = None,
    target: str | None = None,
    severity: str = "info",
    payload: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """Append one event. Returns the new event id."""
    if severity not in ("info", "warn", "critical"):
        severity = "info"
    now = datetime.now(timezone.utc).isoformat()
    db = _conn(db_path)
    try:
        cur = db.execute(
            "INSERT INTO events (ts, kind, actor, target, severity, payload) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now, kind, actor, target, severity, json.dumps(payload or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def recent(
    kind: str | None = None,
    actor: str | None = None,
    since: str | None = None,
    minutes: int | None = None,
    limit: int = 200,
    db_path: Path | None = None,
) -> list[dict]:
    """Recent events; flexible filter."""
    if minutes and not since:
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    conditions = []
    params: list[Any] = []
    if kind:
        conditions.append("kind = ?")
        params.append(kind)
    if actor:
        conditions.append("actor = ?")
        params.append(actor)
    if since:
        conditions.append("ts >= ?")
        params.append(since)
    where = " AND ".join(conditions) if conditions else "1"

    db = _conn(db_path)
    try:
        rows = db.execute(
            f"SELECT * FROM events WHERE {where} ORDER BY ts DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def rollup_hour(end_ts: str | None = None, db_path: Path | None = None) -> int:
    """Aggregate events into the events_hourly table for the previous hour.
    Returns the number of (bucket, kind, severity) rows written."""
    end = datetime.fromisoformat(end_ts) if end_ts else datetime.now(timezone.utc)
    end = end.replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=1)
    bucket = start.isoformat()

    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT kind, severity, COUNT(*) AS n FROM events "
            "WHERE ts >= ? AND ts < ? GROUP BY kind, severity",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        for r in rows:
            db.execute(
                "INSERT INTO events_hourly (bucket_ts, kind, severity, count) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(bucket_ts, kind, severity) DO UPDATE SET count = excluded.count",
                (bucket, r["kind"], r["severity"], int(r["n"])),
            )
        db.commit()
        return len(rows)
    finally:
        db.close()


__all__ = ["init_events_db", "append", "recent", "rollup_hour", "SCHEMA_VERSION"]
