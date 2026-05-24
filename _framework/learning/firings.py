# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Firings — the fifth link in the seven-step loop.

When a model uses an injected rule to shape an action, the skill
records a firing. This is how the framework knows the loop is
actually working (vs. rules being injected and ignored).

The model is prompted to record firings as part of its action loop;
skills include a "Step N: Record firings" instruction (scaffold-skill
inserts by default). Hard rules ALSO record via the send-guard /
verifier when they catch a violation attempt (was_overridden=1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .learning_db import get_db


@dataclass
class FiringRecord:
    id: int
    rule_id: str
    skill_tag: str
    profile: str
    was_overridden: bool
    action_summary: str | None
    created_at: str


def record_firing(
    rule_id: str,
    skill_tag: str,
    profile: str,
    was_overridden: bool = False,
    action_summary: str | None = None,
    db_path=None,
) -> int:
    """Persist a firing. Returns the new firings.id.

    Raises ValueError on missing args; the schema's FK will enforce
    rule_id existence.
    """
    if not rule_id:
        raise ValueError("rule_id required")
    if not skill_tag:
        raise ValueError("skill_tag required")
    if not profile:
        raise ValueError("profile required")

    now = datetime.now(timezone.utc).isoformat()
    db = get_db(path=db_path)
    try:
        cur = db.execute(
            "INSERT INTO firings (rule_id, skill_tag, profile, was_overridden, action_summary, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rule_id, skill_tag, profile, 1 if was_overridden else 0, action_summary or "", now),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def for_rule(rule_id: str, limit: int = 50, db_path=None) -> list[FiringRecord]:
    """Recent firings for one rule, newest first."""
    db = get_db(path=db_path)
    try:
        rows = db.execute(
            "SELECT * FROM firings WHERE rule_id=? ORDER BY created_at DESC LIMIT ?",
            (rule_id, limit),
        ).fetchall()
        return [_row(r) for r in rows]
    finally:
        db.close()


def for_skill(skill_tag: str, days: int = 30, db_path=None) -> list[FiringRecord]:
    """Recent firings for one skill across all rules."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_db(path=db_path)
    try:
        rows = db.execute(
            "SELECT * FROM firings WHERE skill_tag=? AND created_at>=? ORDER BY created_at DESC",
            (skill_tag, cutoff),
        ).fetchall()
        return [_row(r) for r in rows]
    finally:
        db.close()


def count_for_skill_in_days(skill_tag: str, days: int, db_path=None) -> int:
    """Return how many firings recorded for skill_tag in last `days` days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_db(path=db_path)
    try:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM firings WHERE skill_tag=? AND created_at>=?",
            (skill_tag, cutoff),
        ).fetchone()
        return int(row["n"])
    finally:
        db.close()


def override_rate(rule_id: str, days: int = 30, db_path=None) -> float:
    """For hard rules: what fraction of recent firings were override attempts?
    Returns 0.0 if there are no firings."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = get_db(path=db_path)
    try:
        row = db.execute(
            "SELECT COUNT(*) AS n, SUM(was_overridden) AS o "
            "FROM firings WHERE rule_id=? AND created_at>=?",
            (rule_id, cutoff),
        ).fetchone()
        n = int(row["n"]) if row["n"] else 0
        o = int(row["o"]) if row["o"] else 0
        return 0.0 if n == 0 else o / n
    finally:
        db.close()


def _row(r) -> FiringRecord:
    return FiringRecord(
        id=int(r["id"]),
        rule_id=str(r["rule_id"]),
        skill_tag=str(r["skill_tag"]),
        profile=str(r["profile"]),
        was_overridden=bool(r["was_overridden"]),
        action_summary=r["action_summary"],
        created_at=str(r["created_at"]),
    )


__all__ = [
    "FiringRecord",
    "record_firing",
    "for_rule",
    "for_skill",
    "count_for_skill_in_days",
    "override_rate",
]
