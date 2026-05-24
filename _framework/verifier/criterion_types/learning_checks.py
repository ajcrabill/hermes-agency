# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Learning-loop criteria — the ones that prove a skill exercised the spine.

  learning_rule_recorded   a capture happened in this task's window
  firing_recorded          a firing was recorded for this (rule, skill) pair
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from _framework.verifier.registry import register


@register("learning_rule_recorded")
def learning_rule_recorded(args: dict) -> tuple[bool, str]:
    """
    Pass if at least one learning rule was captured matching the filter
    within `minutes_window` (default 60) of now.

    args:
      source_contains: substring to look for in learning_rules.source
      minutes_window:  default 60
    """
    needle = args.get("source_contains", "")
    window = int(args.get("minutes_window", 60))
    try:
        from _framework.learning.learning_db import get_db
    except Exception as e:
        return False, f"learning subsystem unavailable: {e}"
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window)).isoformat()
    db = get_db()
    try:
        q = "SELECT COUNT(*) AS n FROM learning_rules WHERE created_at >= ?"
        params: list = [cutoff]
        if needle:
            q += " AND source LIKE ?"
            params.append(f"%{needle}%")
        n = int(db.execute(q, params).fetchone()["n"])
    finally:
        db.close()
    if n > 0:
        return True, f"{n} learning rule(s) captured in last {window}m matching '{needle}'"
    return False, f"no learning rules captured in last {window}m matching '{needle}'"


@register("firing_recorded")
def firing_recorded(args: dict) -> tuple[bool, str]:
    """
    Pass if at least one firing was recorded for the (rule_id, skill_tag)
    pair within `minutes_window` (default 60).

    args:
      rule_id:   the learning rule id
      skill_tag: the skill that fired
      minutes_window: default 60
    """
    rule_id = args.get("rule_id")
    skill_tag = args.get("skill_tag")
    if not rule_id or not skill_tag:
        return False, "args.rule_id and args.skill_tag required"
    window = int(args.get("minutes_window", 60))
    try:
        from _framework.learning.learning_db import get_db
    except Exception as e:
        return False, f"learning subsystem unavailable: {e}"
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window)).isoformat()
    db = get_db()
    try:
        n = int(db.execute(
            "SELECT COUNT(*) AS n FROM firings WHERE rule_id=? AND skill_tag=? AND created_at>=?",
            (rule_id, skill_tag, cutoff),
        ).fetchone()["n"])
    finally:
        db.close()
    if n > 0:
        return True, f"{n} firing(s) recorded for ({rule_id}, {skill_tag}) in last {window}m"
    return False, f"no firings recorded for ({rule_id}, {skill_tag}) in last {window}m"
