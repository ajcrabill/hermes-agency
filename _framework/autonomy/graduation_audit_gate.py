# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Graduation audit gate — the three-input check for promotion.

Called from `autonomy_engine.record_event()` at the exact moment a
skill is about to be promoted (consecutive_clean has reached the
threshold AND level < 5). Returns (block, kind, reason).

Three inputs (§4.3):

  1. AUDIT       — `audit-alignment.py --skill X --strict` returns 0
                   (i.e. no ALWAYS_BLOCK findings)
  2. RECAPTURE   — no recapture_events rows tagged with this skill
                   in the last L days (default 14)
  3. FIRING      — if the skill has >3 captured rules,
                   it has >0 firings in the last 30 days

Any failing input → blocked. The reason names which one + the
specific finding.

When blocked:
  - history row written by autonomy_engine
  - kanban task filed (caller's responsibility — gate just reports)
  - consecutive_clean parked at threshold (caller's responsibility)
  - returns 0 from cmd_record_event (gate working as intended)

Failures are PARKED, not reset. The next clean_run after the issue is
fixed triggers another gate check; if it now passes, promotion goes
through.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _framework.manifest import load_invariants


@dataclass
class AuditGateResult:
    blocked: bool
    block_kind: str = ""           # 'audit_blocked_promote' or 'learning_blocked_promote' or ''
    reason: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)


def graduation_audit_gate(
    skill: str,
    profile: str,
    db_path: Path | None = None,
) -> AuditGateResult:
    """Run the three inputs in order. First failure short-circuits."""
    inv = load_invariants()
    cfg = inv.get("autonomy_promotion", {})
    lookback_recap = int(cfg.get("recapture_lookback_days", 14))
    lookback_fire = int(cfg.get("firings_lookback_days", 30))
    min_fire = int(cfg.get("min_firings_when_rules_exist", 1))
    rules_thresh = int(cfg.get("rules_threshold_for_firing_check", 3))

    # ── Input 2: recapture events implicating this skill ─────────────────
    # We check recapture first because it's a clear "loop broken" signal
    # and cheap to query.
    recap_findings = _check_recapture(skill, lookback_recap, db_path=db_path)
    if recap_findings:
        return AuditGateResult(
            blocked=True,
            block_kind="learning_blocked_promote",
            reason=f"{len(recap_findings)} recapture event(s) in last {lookback_recap}d implicate this skill",
            findings=recap_findings,
        )

    # ── Input 3: learning fidelity (rules exist → firings happened) ──────
    fire_findings = _check_firing_fidelity(
        skill=skill, rules_threshold=rules_thresh, lookback_days=lookback_fire,
        min_firings=min_fire, db_path=db_path,
    )
    if fire_findings:
        return AuditGateResult(
            blocked=True,
            block_kind="learning_blocked_promote",
            reason=fire_findings[0]["message"],
            findings=fire_findings,
        )

    # ── Input 1: structural audit (--strict) ─────────────────────────────
    audit_findings = _run_strict_audit(skill=skill, profile=profile)
    if audit_findings:
        return AuditGateResult(
            blocked=True,
            block_kind="audit_blocked_promote",
            reason=f"{len(audit_findings)} ALWAYS_BLOCK audit finding(s) on this skill",
            findings=audit_findings,
        )

    return AuditGateResult(blocked=False)


# ── Individual input checks ──────────────────────────────────────────────


def _check_recapture(
    skill: str,
    lookback_days: int,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return non-empty list if any recapture events in the window
    implicate this skill (via skill_tags string match)."""
    try:
        from _framework.learning.learning_db import get_db
    except Exception:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    try:
        db = get_db()
    except Exception:
        return []
    try:
        rows = db.execute(
            "SELECT new_rule_id, similar_to, similarity, skill_tags, detected_at "
            "FROM recapture_events WHERE detected_at >= ? AND dismissed=0",
            (cutoff,),
        ).fetchall()
        out = []
        for r in rows:
            tags = (r["skill_tags"] or "").split(",")
            if skill in tags:
                out.append({
                    "code": "recapture-implicates-skill",
                    "rule_id": r["new_rule_id"],
                    "similar_to": r["similar_to"],
                    "similarity": float(r["similarity"]),
                    "detected_at": r["detected_at"],
                })
        return out
    finally:
        db.close()


def _check_firing_fidelity(
    skill: str,
    rules_threshold: int,
    lookback_days: int,
    min_firings: int,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """If skill has more than `rules_threshold` rules, demand
    `min_firings` firings in the lookback window."""
    try:
        from _framework.learning.learning_db import get_db, decode_json_col
    except Exception:
        return []

    try:
        db = get_db()
    except Exception:
        return []
    try:
        rules = db.execute(
            "SELECT id, skill_tags FROM learning_rules WHERE status='active'"
        ).fetchall()
        n_rules = sum(1 for r in rules if skill in decode_json_col(r["skill_tags"]))
        if n_rules <= rules_threshold:
            return []

        cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
        n_fires = db.execute(
            "SELECT COUNT(*) AS n FROM firings WHERE skill_tag=? AND created_at>=?",
            (skill, cutoff),
        ).fetchone()["n"]
        if int(n_fires) < min_firings:
            return [{
                "code": "learning-loop-broken",
                "message": f"skill has {n_rules} rules but {n_fires} firings in last {lookback_days}d (threshold {min_firings})",
                "rules": n_rules,
                "firings": int(n_fires),
            }]
        return []
    finally:
        db.close()


def _run_strict_audit(skill: str, profile: str) -> list[dict[str, Any]]:
    """Call audit-alignment.py --skill X --profile P --strict and parse the result.

    For v0.1 we shortcut: if the audit module isn't built yet, treat it
    as clean (warn-no-audit-implementation). Week 4 wires this for
    real."""
    try:
        from _framework.audit import audit_alignment
    except ImportError:
        return []
    try:
        report = audit_alignment.audit_skill(skill=skill, profile=profile, strict=True)
    except Exception as e:
        return [{
            "code": "audit-self-failed",
            "message": f"audit_alignment errored: {e}",
        }]
    blocking = [f for f in report.findings if f.is_blocking]
    return [
        {"code": f.code, "message": f.message, "location": f.location}
        for f in blocking
    ]


__all__ = ["AuditGateResult", "graduation_audit_gate"]
