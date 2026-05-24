# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
autonomy_engine — promote/demote logic + the three-input gate.

Public entry points:
  - record_event(...)        the canonical event recorder; runs through
                             the graduation gate at promotion-decision
                             points and routes accordingly
  - promote(...)             explicit promote (still gated)
  - demote(...)              explicit demote
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from _framework.manifest import load_invariants
from .autonomy_db import _conn, init_autonomy_db


@dataclass
class Promotion:
    skill: str
    profile: str
    from_level: int
    to_level: int
    reason: str
    blocked: bool = False           # if True: gate refused
    blocker: str = ""


@dataclass
class Demotion:
    skill: str
    profile: str
    from_level: int
    to_level: int
    reason: str


# ── Event recorder ───────────────────────────────────────────────────────


def record_event(
    skill: str,
    profile: str,
    kind: str,
    payload: dict | None = None,
    db_path: Path | None = None,
) -> Promotion | Demotion | None:
    """
    Record an autonomy event and apply state transitions.

    `kind`:
      clean_run     — a successful run; counter increments; promote when threshold reached
      failure       — a failed run; counter resets; demote one level
      audit_blocked_promote — recorded by graduation gate; counter is parked at threshold
      learning_blocked_promote — recorded by gate; same shape
      manual_set    — operator override; counter reset; history recorded

    Returns the Promotion / Demotion that resulted, if any.
    """
    init_autonomy_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    inv = load_invariants()
    thresh = int(inv.get("autonomy_promotion", {}).get("consecutive_clean_runs", 5))

    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT level, consecutive_clean FROM skill_autonomy WHERE skill=? AND profile=?",
            (skill, profile),
        ).fetchone()
        if row is None:
            level = 1
            consec = 0
            db.execute(
                "INSERT INTO skill_autonomy(skill, profile, level, consecutive_clean, last_event_ts, last_event_kind) "
                "VALUES (?, ?, 1, 0, ?, ?)",
                (skill, profile, now, kind),
            )
        else:
            level = int(row["level"])
            consec = int(row["consecutive_clean"])

        result: Promotion | Demotion | None = None

        if kind == "clean_run":
            consec += 1
            if consec >= thresh and level < 5:
                # promotion decision point — graduation gate runs here
                from .graduation_audit_gate import graduation_audit_gate
                gate = graduation_audit_gate(skill=skill, profile=profile, db_path=db_path)
                if gate.blocked:
                    # Park counter at threshold; record blocked-promote in history
                    db.execute(
                        "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason, payload) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            now, skill, profile,
                            gate.block_kind,           # 'audit_blocked_promote' or 'learning_blocked_promote'
                            level, level,
                            gate.reason,
                            json.dumps(gate.findings or []),
                        ),
                    )
                    db.execute(
                        "UPDATE skill_autonomy SET consecutive_clean=?, last_event_ts=?, last_event_kind=? "
                        "WHERE skill=? AND profile=?",
                        (consec, now, gate.block_kind, skill, profile),
                    )
                    db.commit()
                    return Promotion(
                        skill=skill, profile=profile,
                        from_level=level, to_level=level,
                        reason=gate.reason,
                        blocked=True, blocker=gate.block_kind,
                    )
                # gate allows promotion
                new_level = level + 1
                db.execute(
                    "UPDATE skill_autonomy SET level=?, consecutive_clean=0, last_event_ts=?, last_event_kind='promote' "
                    "WHERE skill=? AND profile=?",
                    (new_level, now, skill, profile),
                )
                db.execute(
                    "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason) "
                    "VALUES (?, ?, ?, 'promote', ?, ?, ?)",
                    (now, skill, profile, level, new_level, "three-input gate passed"),
                )
                db.commit()
                return Promotion(skill=skill, profile=profile, from_level=level, to_level=new_level, reason="three-input gate passed")
            else:
                # Increment counter, no promotion
                db.execute(
                    "UPDATE skill_autonomy SET consecutive_clean=?, last_event_ts=?, last_event_kind='clean_run' "
                    "WHERE skill=? AND profile=?",
                    (consec, now, skill, profile),
                )
                db.execute(
                    "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason) "
                    "VALUES (?, ?, ?, 'clean_run', ?, ?, ?)",
                    (now, skill, profile, level, level, f"consec={consec}/{thresh}"),
                )
                db.commit()
                return None

        if kind == "failure":
            new_level = max(1, level - 1)
            reason = (payload or {}).get("reason", "failure")
            db.execute(
                "UPDATE skill_autonomy SET level=?, consecutive_clean=0, last_event_ts=?, last_event_kind='demote' "
                "WHERE skill=? AND profile=?",
                (new_level, now, skill, profile),
            )
            db.execute(
                "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason, payload) "
                "VALUES (?, ?, ?, 'failure', ?, ?, ?, ?)",
                (now, skill, profile, level, new_level, reason, json.dumps(payload or {})),
            )
            db.commit()
            return Demotion(skill=skill, profile=profile, from_level=level, to_level=new_level, reason=reason)

        # Unknown kind — record as history but don't mutate state
        db.execute(
            "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now, skill, profile, kind, level, level, "unknown event kind", json.dumps(payload or {})),
        )
        db.commit()
        return None
    finally:
        db.close()


def promote(skill: str, profile: str, reason: str = "manual-promote", db_path: Path | None = None) -> Promotion:
    """Explicit promote — still goes through the graduation gate."""
    from .graduation_audit_gate import graduation_audit_gate
    init_autonomy_db(db_path)
    now = datetime.now(timezone.utc).isoformat()

    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT level FROM skill_autonomy WHERE skill=? AND profile=?",
            (skill, profile),
        ).fetchone()
        level = int(row["level"]) if row else 1
        if level >= 5:
            return Promotion(skill=skill, profile=profile, from_level=level, to_level=level, reason="already at L5")

        gate = graduation_audit_gate(skill=skill, profile=profile, db_path=db_path)
        if gate.blocked:
            db.execute(
                "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now, skill, profile, gate.block_kind, level, level, gate.reason),
            )
            db.commit()
            return Promotion(
                skill=skill, profile=profile, from_level=level, to_level=level,
                reason=gate.reason, blocked=True, blocker=gate.block_kind,
            )

        new_level = level + 1
        if row:
            db.execute(
                "UPDATE skill_autonomy SET level=?, consecutive_clean=0, last_event_ts=?, last_event_kind='promote' "
                "WHERE skill=? AND profile=?",
                (new_level, now, skill, profile),
            )
        else:
            db.execute(
                "INSERT INTO skill_autonomy(skill, profile, level, consecutive_clean, last_event_ts, last_event_kind) "
                "VALUES (?, ?, ?, 0, ?, 'promote')",
                (skill, profile, new_level, now),
            )
        db.execute(
            "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason) "
            "VALUES (?, ?, ?, 'promote', ?, ?, ?)",
            (now, skill, profile, level, new_level, reason),
        )
        db.commit()
        return Promotion(skill=skill, profile=profile, from_level=level, to_level=new_level, reason=reason)
    finally:
        db.close()


def demote(skill: str, profile: str, reason: str = "manual-demote", db_path: Path | None = None) -> Demotion:
    """Explicit demote — no gate; demotion is always allowed."""
    init_autonomy_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT level FROM skill_autonomy WHERE skill=? AND profile=?",
            (skill, profile),
        ).fetchone()
        level = int(row["level"]) if row else 1
        new_level = max(1, level - 1)
        if row:
            db.execute(
                "UPDATE skill_autonomy SET level=?, consecutive_clean=0, last_event_ts=?, last_event_kind='demote' "
                "WHERE skill=? AND profile=?",
                (new_level, now, skill, profile),
            )
        else:
            db.execute(
                "INSERT INTO skill_autonomy(skill, profile, level, consecutive_clean, last_event_ts, last_event_kind) "
                "VALUES (?, ?, 1, 0, ?, 'demote')",
                (skill, profile, now),
            )
        db.execute(
            "INSERT INTO skill_autonomy_history(ts, skill, profile, kind, from_level, to_level, reason) "
            "VALUES (?, ?, ?, 'demote', ?, ?, ?)",
            (now, skill, profile, level, new_level, reason),
        )
        db.commit()
        return Demotion(skill=skill, profile=profile, from_level=level, to_level=new_level, reason=reason)
    finally:
        db.close()


__all__ = ["Promotion", "Demotion", "record_event", "promote", "demote"]
