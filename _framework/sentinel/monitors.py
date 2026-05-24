# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Sentinel cron entry points.

Each function runs as a scheduled job and emits one or more events
into events.db. None of these mutate state outside Sentinel's own
table; if any one of them notices a problem, the response is a
kanban task — never a fix.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .events_db import append as _emit


def learning_monitor() -> dict[str, Any]:
    """
    Every 5m: look at recapture_events that haven't been notified yet.
    For each: emit a `recapture_detected` event + (caller's job) file
    a kanban task. Returns a summary of what fired.
    """
    try:
        from _framework.learning.learning_db import get_db
    except Exception as e:
        _emit("learning_monitor_failed", actor="sentinel", severity="critical",
              payload={"error": str(e)})
        return {"error": str(e)}

    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, new_rule_id, similar_to, similarity, skill_tags, detected_at "
            "FROM recapture_events WHERE notified=0 AND dismissed=0 "
            "ORDER BY detected_at DESC LIMIT 20"
        ).fetchall()
        for r in rows:
            _emit(
                "recapture_detected",
                actor="sentinel",
                target=r["new_rule_id"],
                severity="critical",
                payload={
                    "similar_to": r["similar_to"],
                    "similarity": float(r["similarity"]),
                    "skill_tags": r["skill_tags"],
                    "detected_at": r["detected_at"],
                },
            )
            db.execute("UPDATE recapture_events SET notified=1 WHERE id=?", (r["id"],))
        db.commit()
    finally:
        db.close()
    return {"recaptures_notified": len(rows)}


def drift_monitor() -> dict[str, Any]:
    """
    Every 15m: compute per-skill drift score from the audit's most
    recent run (changes in finding counts over the last 7 days).
    Updates _state/drift_scores.json and emits a drift event if any
    skill jumped above threshold.

    For v0.1: skeleton that reads audit history if present; emits
    nothing if no audit history exists yet.
    """
    try:
        from _framework.constants import AUDITS_DIR
    except Exception:
        return {"skipped": "no constants"}

    if not AUDITS_DIR.exists():
        return {"skipped": "no audit history yet"}
    # Minimal v0.1 implementation: drift tracking expands as the audit
    # produces more history. Emit a heartbeat event so the operator sees
    # the monitor is alive.
    _emit("drift_monitor_run", actor="sentinel", severity="info",
          payload={"audits_dir_exists": True})
    return {"ran": True}


def heartbeat_watch() -> dict[str, Any]:
    """
    Every 5m: walk `_state/heartbeats.db` if present. If any component
    hasn't beat in 2x its expected interval, emit `heartbeat_stale`
    event.
    """
    from pathlib import Path
    from _framework.constants import HEARTBEATS_DB
    from _framework.manifest import load_invariants

    if not Path(HEARTBEATS_DB).exists():
        return {"skipped": "heartbeats.db not yet populated"}

    import sqlite3
    inv = load_invariants()
    expected = inv.get("expected_intervals_seconds", {})
    now = datetime.now(timezone.utc)
    stale = []
    try:
        c = sqlite3.connect(str(HEARTBEATS_DB))
        c.row_factory = sqlite3.Row
        # Heartbeats table shape: (component TEXT, last_success_at TEXT)
        rows = c.execute(
            "SELECT component, last_success_at FROM heartbeats"
        ).fetchall()
        c.close()
    except sqlite3.OperationalError:
        return {"skipped": "heartbeats schema not initialized"}

    for r in rows:
        comp = r["component"]
        last = r["last_success_at"]
        if not last:
            continue
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            continue
        cadence = expected.get(comp, 300)   # default 5m
        max_age = timedelta(seconds=cadence * 2)
        if now - last_dt > max_age:
            stale.append({"component": comp, "last_success_at": last, "age_seconds": (now - last_dt).total_seconds()})
            _emit(
                "heartbeat_stale",
                actor="sentinel",
                target=comp,
                severity="warn",
                payload={"last_success_at": last, "expected_interval": cadence},
            )
    return {"stale": stale}


def event_rollup() -> dict[str, Any]:
    """Hourly: roll up the last hour's events into events_hourly."""
    from .events_db import rollup_hour
    n = rollup_hour()
    _emit("event_rollup_ran", actor="sentinel", payload={"buckets_written": n})
    return {"buckets_written": n}


def compliance_report() -> str:
    """Sundays 06:00: generate the weekly compliance report."""
    from _framework.learning.compliance_report import weekly_compliance_report
    md = weekly_compliance_report()
    _emit("compliance_report_generated", actor="sentinel", severity="info",
          payload={"length_chars": len(md)})
    return md


def playbook_audit() -> dict[str, Any]:
    """Sundays 04:00: full fleet audit."""
    try:
        from _framework.audit import audit_alignment
    except ImportError:
        _emit("playbook_audit_skipped", actor="sentinel", severity="warn",
              payload={"reason": "audit module not yet built"})
        return {"skipped": "no audit module"}

    report = audit_alignment.audit_deployment()
    n_block = sum(1 for f in report.findings if f.is_blocking)
    n_warn = len(report.findings) - n_block
    _emit(
        "playbook_audit_ran",
        actor="sentinel",
        severity="critical" if n_block else ("warn" if n_warn else "info"),
        payload={"blocking": n_block, "warnings": n_warn, "rules": list(report.rules_run)},
    )
    return {"blocking": n_block, "warnings": n_warn}


def guardrails_watch() -> dict[str, Any]:
    """At session boundaries (on_session_start / on_session_end):
    load Guardrails.md and report on the **Interim Guardrails** —
    the SMART, objectively-measurable layer beneath each Guardrail.

    Sentinel is the architectural watchdog (per v0.22.4-spec); the
    Guardrails.md file is the content it watches against. **The
    Guardrails themselves are value statements and not directly
    measurable** — what Sentinel observes is the Interim Guardrails
    (SMART metrics with start/end dates and start/end points). If
    the Interim Guardrails are within parameter, we infer the
    Guardrail is being honored. If an Interim Guardrail drifts,
    the Guardrail is at risk.

    This function doesn't enforce — it observes and emits events
    for the Principal to review.

    Returns a summary: how many Interim Guardrails are tracked
    (Guardrail counts are reported but are not the measured layer).
    """
    try:
        from _framework.guardrails_loader import load_guardrails_parsed
    except ImportError as e:
        _emit("guardrails_watch_skipped", actor="sentinel", severity="warn",
              payload={"reason": f"loader unavailable: {e}"})
        return {"skipped": True}

    parsed = load_guardrails_parsed()
    if parsed is None:
        # No Guardrails.md yet — emit info-level so the audit
        # 'agency-context-injection' rule has signal but Sentinel
        # itself doesn't escalate.
        _emit("guardrails_watch_no_doc", actor="sentinel", severity="info",
              payload={"hint": "Guardrails.md not present"})
        return {"interim_guardrails_tracked": 0}

    guardrails = parsed.get("guardrails", [])
    # Roll up Interim Guardrails — the measurable layer. The
    # Guardrails themselves are value statements; we just count
    # them for context.
    interim_count = sum(
        len(g.get("interim_guardrails", [])) for g in guardrails
    )
    interim_without_initiatives = sum(
        1
        for g in guardrails
        for ig in g.get("interim_guardrails", [])
        if not ig.get("initiative_refs")
    )

    _emit(
        "guardrails_watch_ran",
        actor="sentinel",
        severity="info",
        payload={
            "guardrails_in_scope": len(guardrails),
            "interim_guardrails_tracked": interim_count,
            "interim_without_initiatives": interim_without_initiatives,
            "note": (
                "Guardrails are value statements (not measurable); "
                "monitoring works on Interim Guardrails — SMART metrics "
                "under each Guardrail. If Interim Guardrails are within "
                "parameter, the Guardrail is inferred honored."
            ),
        },
    )

    # An Interim Guardrail without resourced Initiatives is a
    # warning sign: nothing is producing the artifact that would
    # move the metric.
    if interim_without_initiatives:
        _emit(
            "interim_guardrail_unresourced",
            actor="sentinel",
            severity="warn",
            payload={
                "count": interim_without_initiatives,
                "hint": "Some Interim Guardrails have no skill/script Initiatives attached.",
            },
        )

    return {
        "guardrails_in_scope": len(guardrails),
        "interim_guardrails_tracked": interim_count,
        "interim_without_initiatives": interim_without_initiatives,
    }


__all__ = [
    "learning_monitor",
    "drift_monitor",
    "heartbeat_watch",
    "event_rollup",
    "compliance_report",
    "playbook_audit",
    "guardrails_watch",
]
