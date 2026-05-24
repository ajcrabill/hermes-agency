# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Goal tracking — measurable progress against SMART goals.

Goals.md defines what matters. This module records the actual numbers
over time + computes status (on-track / at-risk / missed) against
the deadlines + targets in interim milestones.

Schema:
  goal_metrics       one row per (goal, metric_name). Describes
                     WHAT to measure + WHERE the data comes from.
  goal_observations  recorded values over time per metric.
  goal_milestones    parsed from Goals.md interim bullets, with
                     target deadline + status.

The framework provides the substrate. Operators (or the CoS
`goal-progress-tracker` skill) define metrics + record observations
+ produce weekly reports.

Status computation:
  on-track     — current observation ≥ projected pace for the deadline
  at-risk      — within 20% of pace, or pace is slowing
  missed       — deadline passed without reaching target
  no-data      — no observations recorded yet
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


GOAL_TRACKING_DB_DEFAULT = STATE_DIR / "goal_tracking.db"
SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_text       TEXT NOT NULL,                   -- matches the bullet in Goals.md
    metric_name     TEXT NOT NULL,                   -- short identifier
    measurement_type TEXT NOT NULL,                  -- counter | gauge | percentage | binary
    unit            TEXT NOT NULL DEFAULT '',        -- e.g. "clients" | "USD" | "%" | "shipped"
    target_value    REAL,                            -- the SMART measurable target
    target_at       TEXT,                            -- the SMART deadline (ISO date)
    data_source     TEXT NOT NULL DEFAULT '',        -- where the value comes from
                                                     --   e.g. "crm.leads WHERE status='converted'"
                                                     --        "manual"
                                                     --        "finance.revenue WHERE source='bd-outreach'"
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    UNIQUE(goal_text, metric_name)
);
CREATE INDEX IF NOT EXISTS idx_gm_goal ON goal_metrics(goal_text);

CREATE TABLE IF NOT EXISTS goal_observations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id       INTEGER NOT NULL REFERENCES goal_metrics(id),
    observed_at     TEXT NOT NULL,
    value           REAL NOT NULL,
    source          TEXT NOT NULL DEFAULT 'manual',  -- manual | crm-sync | finance-sync | etc.
    note            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_go_metric ON goal_observations(metric_id, observed_at);

CREATE TABLE IF NOT EXISTS goal_milestones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_text       TEXT NOT NULL,
    milestone_text  TEXT NOT NULL,                   -- the sub-bullet text
    target_at       TEXT,                            -- parsed deadline if present
    status          TEXT NOT NULL DEFAULT 'pending', -- pending | done | missed | at-risk
    completed_at    TEXT,
    notes           TEXT NOT NULL DEFAULT '',
    UNIQUE(goal_text, milestone_text)
);
CREATE INDEX IF NOT EXISTS idx_gms_goal ON goal_milestones(goal_text);
"""


def init_goal_tracking_db(path: Path | None = None) -> Path:
    target = path or GOAL_TRACKING_DB_DEFAULT
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
    init_goal_tracking_db(path)
    c = sqlite3.connect(str(path or GOAL_TRACKING_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Metrics CRUD ────────────────────────────────────────────────────────


@dataclass
class GoalMetric:
    id: int
    goal_text: str
    metric_name: str
    measurement_type: str
    unit: str
    target_value: float | None
    target_at: str | None
    data_source: str
    notes: str
    created_at: str
    updated_at: str


def define_metric(
    *, goal_text: str, metric_name: str, measurement_type: str,
    unit: str = "", target_value: float | None = None,
    target_at: str | None = None, data_source: str = "manual",
    notes: str = "", db_path: Path | None = None,
) -> int:
    """Define (or update) the metric for a goal. Idempotent on
    (goal_text, metric_name)."""
    if measurement_type not in ("counter", "gauge", "percentage", "binary"):
        raise ValueError(
            f"measurement_type must be one of counter|gauge|percentage|binary, "
            f"got {measurement_type!r}"
        )
    now = _now()
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO goal_metrics (goal_text, metric_name, measurement_type,
                                       unit, target_value, target_at, data_source,
                                       notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(goal_text, metric_name) DO UPDATE SET
                measurement_type = excluded.measurement_type,
                unit = excluded.unit,
                target_value = excluded.target_value,
                target_at = excluded.target_at,
                data_source = excluded.data_source,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (goal_text, metric_name, measurement_type, unit,
             target_value, target_at, data_source, notes, now, now),
        )
        # If it was an update, lastrowid may be 0 — re-fetch
        row = db.execute(
            "SELECT id FROM goal_metrics WHERE goal_text=? AND metric_name=?",
            (goal_text, metric_name),
        ).fetchone()
        db.commit()
        return int(row["id"])
    finally:
        db.close()


def list_metrics(
    *, goal_text: str | None = None, db_path: Path | None = None,
) -> list[GoalMetric]:
    db = _conn(db_path)
    try:
        if goal_text:
            rows = db.execute(
                "SELECT * FROM goal_metrics WHERE goal_text=? ORDER BY metric_name",
                (goal_text,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM goal_metrics ORDER BY goal_text, metric_name"
            ).fetchall()
        return [_row_to_metric(r) for r in rows]
    finally:
        db.close()


def _row_to_metric(r: sqlite3.Row) -> GoalMetric:
    return GoalMetric(
        id=int(r["id"]),
        goal_text=str(r["goal_text"]),
        metric_name=str(r["metric_name"]),
        measurement_type=str(r["measurement_type"]),
        unit=str(r["unit"]),
        target_value=r["target_value"],
        target_at=r["target_at"],
        data_source=str(r["data_source"]),
        notes=str(r["notes"]),
        created_at=str(r["created_at"]),
        updated_at=str(r["updated_at"]),
    )


# ── Observations ────────────────────────────────────────────────────────


def record_observation(
    *, metric_id: int, value: float,
    observed_at: str | None = None, source: str = "manual",
    note: str = "", db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        cur = db.execute(
            "INSERT INTO goal_observations (metric_id, observed_at, value, "
            "source, note) VALUES (?, ?, ?, ?, ?)",
            (metric_id, observed_at or _now(), value, source, note),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def latest_observation(
    metric_id: int, db_path: Path | None = None,
) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT * FROM goal_observations WHERE metric_id=? "
            "ORDER BY observed_at DESC LIMIT 1",
            (metric_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def observation_history(
    metric_id: int, *, days: int = 90,
    db_path: Path | None = None,
) -> list[dict]:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT * FROM goal_observations WHERE metric_id=? AND observed_at>=? "
            "ORDER BY observed_at",
            (metric_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Status computation ──────────────────────────────────────────────────


def metric_status(
    metric_id: int, db_path: Path | None = None,
) -> dict:
    """Compute on-track / at-risk / missed / no-data for a single metric.

    Returns:
      {
        "metric_id": ...,
        "status": "on-track" | "at-risk" | "missed" | "no-data",
        "latest_value": float | None,
        "latest_observed_at": str | None,
        "target_value": float | None,
        "target_at": str | None,
        "pct_of_target": float | None,
        "days_remaining": int | None,
        "reason": str,
      }
    """
    db = _conn(db_path)
    try:
        m_row = db.execute("SELECT * FROM goal_metrics WHERE id=?", (metric_id,)).fetchone()
        if not m_row:
            return {"status": "error", "reason": f"metric {metric_id} not found"}
        latest = db.execute(
            "SELECT * FROM goal_observations WHERE metric_id=? "
            "ORDER BY observed_at DESC LIMIT 1",
            (metric_id,),
        ).fetchone()
    finally:
        db.close()

    target_value = m_row["target_value"]
    target_at_str = m_row["target_at"]
    out: dict[str, Any] = {
        "metric_id": metric_id,
        "metric_name": m_row["metric_name"],
        "goal_text": m_row["goal_text"],
        "measurement_type": m_row["measurement_type"],
        "target_value": target_value,
        "target_at": target_at_str,
        "latest_value": None,
        "latest_observed_at": None,
        "pct_of_target": None,
        "days_remaining": None,
        "status": "no-data",
        "reason": "",
    }

    if latest:
        out["latest_value"] = latest["value"]
        out["latest_observed_at"] = latest["observed_at"]

    if target_value is None or target_value == 0:
        out["status"] = "no-target"
        out["reason"] = "no target_value defined"
        return out

    now = datetime.now(timezone.utc)
    target_at_dt = None
    if target_at_str:
        try:
            # Accept date-only or full ISO
            if "T" not in target_at_str:
                target_at_dt = datetime.fromisoformat(target_at_str + "T23:59:59+00:00")
            else:
                target_at_dt = datetime.fromisoformat(target_at_str)
            out["days_remaining"] = (target_at_dt - now).days
        except Exception:
            target_at_dt = None

    if not latest:
        out["status"] = "no-data"
        out["reason"] = "no observations recorded yet"
        return out

    pct = (latest["value"] / target_value) * 100 if target_value else 0
    out["pct_of_target"] = round(pct, 1)

    if target_at_dt and now > target_at_dt:
        if pct >= 100:
            out["status"] = "done"
            out["reason"] = "target reached"
        else:
            out["status"] = "missed"
            out["reason"] = f"deadline passed; reached {pct:.0f}% of target"
        return out

    # Within window — compute expected pace
    if target_at_dt:
        try:
            created_dt = datetime.fromisoformat(m_row["created_at"])
        except Exception:
            created_dt = now
        total_window_days = max(1, (target_at_dt - created_dt).days)
        elapsed_days = max(0, (now - created_dt).days)
        expected_pct = (elapsed_days / total_window_days) * 100
        out["expected_pct_at_pace"] = round(expected_pct, 1)
        if pct >= expected_pct:
            out["status"] = "on-track"
            out["reason"] = f"{pct:.0f}% achieved vs ~{expected_pct:.0f}% expected at this pace"
        elif pct >= expected_pct * 0.8:
            out["status"] = "at-risk"
            out["reason"] = f"{pct:.0f}% achieved vs ~{expected_pct:.0f}% expected; within 20% of pace"
        else:
            out["status"] = "at-risk"
            out["reason"] = f"behind pace ({pct:.0f}% vs ~{expected_pct:.0f}% expected)"
    else:
        # No deadline — just say where we are
        out["status"] = "on-track" if pct >= 100 else "in-progress"
        out["reason"] = f"{pct:.0f}% of target (no deadline set)"
    return out


def weekly_status_report(
    *, db_path: Path | None = None,
) -> dict:
    """Per-metric status across all defined metrics."""
    metrics = list_metrics(db_path=db_path)
    statuses = [metric_status(m.id, db_path=db_path) for m in metrics]
    summary = {
        "total_metrics": len(metrics),
        "on_track": sum(1 for s in statuses if s["status"] == "on-track"),
        "at_risk": sum(1 for s in statuses if s["status"] == "at-risk"),
        "missed": sum(1 for s in statuses if s["status"] == "missed"),
        "done": sum(1 for s in statuses if s["status"] == "done"),
        "no_data": sum(1 for s in statuses if s["status"] == "no-data"),
        "metrics": statuses,
    }
    return summary


# ── Milestones ──────────────────────────────────────────────────────────


def upsert_milestone(
    *, goal_text: str, milestone_text: str,
    target_at: str | None = None, db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        cur = db.execute(
            "INSERT INTO goal_milestones (goal_text, milestone_text, target_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(goal_text, milestone_text) DO UPDATE SET target_at=excluded.target_at",
            (goal_text, milestone_text, target_at),
        )
        row = db.execute(
            "SELECT id FROM goal_milestones WHERE goal_text=? AND milestone_text=?",
            (goal_text, milestone_text),
        ).fetchone()
        db.commit()
        return int(row["id"])
    finally:
        db.close()


def mark_milestone(
    milestone_id: int, *, status: str, completed_at: str | None = None,
    notes: str = "", db_path: Path | None = None,
) -> None:
    if status not in ("pending", "done", "missed", "at-risk"):
        raise ValueError(f"invalid status {status!r}")
    db = _conn(db_path)
    try:
        db.execute(
            "UPDATE goal_milestones SET status=?, completed_at=?, notes=? WHERE id=?",
            (status, completed_at, notes, milestone_id),
        )
        db.commit()
    finally:
        db.close()


def list_milestones(
    *, goal_text: str | None = None, status: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    db = _conn(db_path)
    try:
        conditions = []
        params: list[Any] = []
        if goal_text:
            conditions.append("goal_text=?")
            params.append(goal_text)
        if status:
            conditions.append("status=?")
            params.append(status)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = db.execute(
            f"SELECT * FROM goal_milestones{where} ORDER BY target_at NULLS LAST", params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def sync_milestones_from_goals_md(db_path: Path | None = None) -> int:
    """Read Goals.md, upsert milestones for each annual goal's sub-bullets.
    Returns the number of milestones synced."""
    from .goals_md import read_goals
    parsed = read_goals()
    n = 0
    for goal in parsed.annual_goals:
        for interim in goal.interim:
            target_at = _extract_date_hint(interim)
            upsert_milestone(
                goal_text=goal.text,
                milestone_text=interim,
                target_at=target_at,
                db_path=db_path,
            )
            n += 1
    return n


_DATE_HINTS_RE = None
def _extract_date_hint(text: str) -> str | None:
    """Heuristic: pull a 'Q3', 'November 2026', 'by 2026-09-30' etc. out
    of a milestone string. Returns ISO date or None.

    Quarter-end mapping (current year unless year explicit):
      Q1 → 03-31, Q2 → 06-30, Q3 → 09-30, Q4 → 12-31.
    """
    import re
    if not text:
        return None
    now = datetime.now(timezone.utc)
    year = now.year
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        year = int(year_match.group(1))
    # Q-quarter mapping
    q_match = re.search(r"\bQ([1-4])\b", text)
    if q_match:
        q = int(q_match.group(1))
        month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[q]
        return f"{year}-{month_day}"
    # ISO date
    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        y, m, d = iso_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    # Month name
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
        "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12,
    }
    for name, num in months.items():
        if name in text.lower():
            # Use end of month as the implicit deadline
            from calendar import monthrange
            day = monthrange(year, num)[1]
            return f"{year:04d}-{num:02d}-{day:02d}"
    return None


__all__ = [
    "GoalMetric",
    "GOAL_TRACKING_DB_DEFAULT",
    "init_goal_tracking_db",
    "define_metric", "list_metrics",
    "record_observation", "latest_observation", "observation_history",
    "metric_status", "weekly_status_report",
    "upsert_milestone", "mark_milestone", "list_milestones",
    "sync_milestones_from_goals_md",
]
