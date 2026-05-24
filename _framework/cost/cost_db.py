# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
cost.db — inference call records + per-skill budgets.

Tokens stored as integers. Cost stored in micro-units of the
currency (1/1,000,000 of a unit) for sub-cent precision on very
cheap models.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


COST_DB_DEFAULT = STATE_DIR / "cost.db"
SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inference_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    skill           TEXT NOT NULL,
    profile         TEXT,
    role            TEXT,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    tokens_in       INTEGER NOT NULL DEFAULT 0,
    tokens_out      INTEGER NOT NULL DEFAULT 0,
    cost_micro      INTEGER NOT NULL DEFAULT 0,       -- micro-units of currency
    currency        TEXT NOT NULL DEFAULT 'USD',
    duration_ms     INTEGER,
    task_id         TEXT,
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ic_skill_ts ON inference_calls(skill, ts);
CREATE INDEX IF NOT EXISTS idx_ic_profile_ts ON inference_calls(profile, ts);
CREATE INDEX IF NOT EXISTS idx_ic_ts ON inference_calls(ts);

CREATE TABLE IF NOT EXISTS cost_budgets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    skill           TEXT,                            -- nullable — null = role/global budget
    role            TEXT,                            -- nullable — null = skill/global budget
    period          TEXT NOT NULL,                   -- 'daily' | 'weekly' | 'monthly'
    limit_micro     INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    block_at_level  INTEGER NOT NULL DEFAULT 4,     -- block skills at L >= this when over budget
    note            TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    UNIQUE(skill, role, period)
);
"""


@dataclass
class InferenceCall:
    id: int
    ts: str
    skill: str
    profile: str | None
    role: str | None
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_micro: int
    currency: str
    duration_ms: int | None = None
    task_id: str | None = None


@dataclass
class BudgetVerdict:
    over_budget: bool
    period: str
    period_start: str
    spent_micro: int
    limit_micro: int
    currency: str
    block_at_level: int
    reason: str


def init_cost_db(path: Path | None = None) -> Path:
    target = path or COST_DB_DEFAULT
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
    init_cost_db(path)
    c = sqlite3.connect(str(path or COST_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Record + query ──────────────────────────────────────────────────────


def record_inference_call(
    *, skill: str, provider: str, model: str,
    tokens_in: int = 0, tokens_out: int = 0,
    profile: str | None = None, role: str | None = None,
    cost_micro: int | None = None, currency: str = "USD",
    duration_ms: int | None = None, task_id: str | None = None,
    metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Record one inference call. If cost_micro is None, the framework
    tries to compute it via the registered pricer for (provider, model)."""
    if cost_micro is None:
        from .pricing import compute_cost_cents
        cost_cents = compute_cost_cents(provider=provider, model=model,
                                          tokens_in=tokens_in, tokens_out=tokens_out)
        cost_micro = int(cost_cents * 10000)   # cents → micro (1 cent = 10,000 micro)
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO inference_calls (ts, skill, profile, role, provider, model,
                                           tokens_in, tokens_out, cost_micro, currency,
                                           duration_ms, task_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now(), skill, profile, role, provider, model,
             tokens_in, tokens_out, cost_micro, currency,
             duration_ms, task_id, json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def list_inference_calls(
    *, skill: str | None = None, profile: str | None = None,
    since_days: int = 7, limit: int = 500,
    db_path: Path | None = None,
) -> list[InferenceCall]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    db = _conn(db_path)
    try:
        conditions = ["ts >= ?"]
        params: list[Any] = [cutoff]
        if skill:
            conditions.append("skill=?")
            params.append(skill)
        if profile:
            conditions.append("profile=?")
            params.append(profile)
        where = " AND ".join(conditions)
        rows = db.execute(
            f"SELECT * FROM inference_calls WHERE {where} ORDER BY ts DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [_row_to_call(r) for r in rows]
    finally:
        db.close()


def _row_to_call(r: sqlite3.Row) -> InferenceCall:
    return InferenceCall(
        id=int(r["id"]),
        ts=str(r["ts"]),
        skill=str(r["skill"]),
        profile=r["profile"],
        role=r["role"],
        provider=str(r["provider"]),
        model=str(r["model"]),
        tokens_in=int(r["tokens_in"]),
        tokens_out=int(r["tokens_out"]),
        cost_micro=int(r["cost_micro"]),
        currency=str(r["currency"]),
        duration_ms=r["duration_ms"],
        task_id=r["task_id"],
    )


# ── Rollups ─────────────────────────────────────────────────────────────


def skill_totals(*, since_days: int = 7, db_path: Path | None = None) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT skill, COUNT(*) AS n, SUM(tokens_in) AS tin, SUM(tokens_out) AS tout, "
            "SUM(cost_micro) AS cost_micro "
            "FROM inference_calls WHERE ts>=? "
            "GROUP BY skill ORDER BY cost_micro DESC",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def role_totals(*, since_days: int = 7, db_path: Path | None = None) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT role, COUNT(*) AS n, SUM(tokens_in) AS tin, SUM(tokens_out) AS tout, "
            "SUM(cost_micro) AS cost_micro "
            "FROM inference_calls WHERE ts>=? AND role IS NOT NULL "
            "GROUP BY role ORDER BY cost_micro DESC",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def daily_totals(*, since_days: int = 30, db_path: Path | None = None) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT substr(ts, 1, 10) AS day, COUNT(*) AS n, "
            "SUM(tokens_in) AS tin, SUM(tokens_out) AS tout, "
            "SUM(cost_micro) AS cost_micro "
            "FROM inference_calls WHERE ts>=? "
            "GROUP BY day ORDER BY day DESC",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Budgets ─────────────────────────────────────────────────────────────


def set_budget(
    *, period: str, limit_micro: int,
    skill: str | None = None, role: str | None = None,
    currency: str = "USD", block_at_level: int = 4,
    note: str = "", db_path: Path | None = None,
) -> int:
    """Define / update a budget for a (skill OR role OR global) + period.

    skill + role both None = global budget; one of them set = scoped.
    """
    if period not in ("daily", "weekly", "monthly"):
        raise ValueError(f"period must be daily|weekly|monthly, got {period!r}")
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO cost_budgets (skill, role, period, limit_micro, currency,
                                        block_at_level, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill, role, period) DO UPDATE SET
                limit_micro = excluded.limit_micro,
                currency = excluded.currency,
                block_at_level = excluded.block_at_level,
                note = excluded.note
            """,
            (skill, role, period, limit_micro, currency, block_at_level,
             note, _now()),
        )
        row = db.execute(
            "SELECT id FROM cost_budgets WHERE COALESCE(skill,'')=? AND COALESCE(role,'')=? AND period=?",
            (skill or "", role or "", period),
        ).fetchone()
        db.commit()
        return int(row["id"])
    finally:
        db.close()


def get_budget(
    *, skill: str | None = None, role: str | None = None,
    period: str = "monthly", db_path: Path | None = None,
) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT * FROM cost_budgets WHERE COALESCE(skill,'')=? "
            "AND COALESCE(role,'')=? AND period=?",
            (skill or "", role or "", period),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def check_budget(
    *, skill: str | None = None, role: str | None = None,
    period: str = "monthly", db_path: Path | None = None,
) -> BudgetVerdict:
    """Is the (skill, role, period) over budget? Returns BudgetVerdict.
    If no budget is set, over_budget=False with reason="no budget defined"."""
    budget = get_budget(skill=skill, role=role, period=period, db_path=db_path)
    period_start = _period_start(period)
    spent = _spent_micro(skill=skill, role=role, since=period_start, db_path=db_path)
    if not budget:
        return BudgetVerdict(
            over_budget=False, period=period, period_start=period_start,
            spent_micro=spent, limit_micro=0, currency="USD",
            block_at_level=4,
            reason="no budget defined",
        )
    over = spent > int(budget["limit_micro"])
    return BudgetVerdict(
        over_budget=over,
        period=period,
        period_start=period_start,
        spent_micro=spent,
        limit_micro=int(budget["limit_micro"]),
        currency=str(budget["currency"]),
        block_at_level=int(budget["block_at_level"]),
        reason=(
            f"spent {spent / 10000:.2f}¢ vs limit {budget['limit_micro'] / 10000:.2f}¢ "
            f"this {period}"
        ),
    )


def _period_start(period: str) -> str:
    now = datetime.now(timezone.utc)
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period == "weekly":
        days_since_monday = now.weekday()
        start = now - timedelta(days=days_since_monday)
        return start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    return now.isoformat()


def _spent_micro(
    *, skill: str | None, role: str | None, since: str,
    db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        conditions = ["ts >= ?"]
        params: list[Any] = [since]
        if skill:
            conditions.append("skill=?")
            params.append(skill)
        if role:
            conditions.append("role=?")
            params.append(role)
        where = " AND ".join(conditions)
        row = db.execute(
            f"SELECT COALESCE(SUM(cost_micro), 0) AS s FROM inference_calls WHERE {where}",
            params,
        ).fetchone()
        return int(row["s"])
    finally:
        db.close()


__all__ = [
    "COST_DB_DEFAULT",
    "InferenceCall", "BudgetVerdict",
    "init_cost_db",
    "record_inference_call", "list_inference_calls",
    "skill_totals", "role_totals", "daily_totals",
    "set_budget", "get_budget", "check_budget",
]
