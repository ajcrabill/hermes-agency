# PLUGIN — owned by HermesAgency.
"""
`/agency` slash-command handler — exposes HermesAgency operations
inside a Hermes session.

Subcommands:
  /agency                          — help text
  /agency status                   — deployment health summary
  /agency next                     — actionable next-steps
  /agency systems                  — 7-system integration inventory
  /agency capture <text>           — capture a learning correction
  /agency learn list [<n>]         — list recent learning rules
  /agency audit                    — run the alignment audit
  /agency health                   — weekly strategic-plan health check (v0.23.6)
  /agency review-prep              — quarterly strategic-review packet (v0.23.7)
  /agency setup                    — migration-or-clean-install interview
                                     (stub in v0.17; full flow in v0.20)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


_HELP_TEXT = """\
/agency — HermesAgency operations

Subcommands:
  status                      Deployment health + Hermes detection
  next                        Actionable next-steps for current state
  systems                     7-system integration inventory
  capture "<correction>"      Capture a learning correction
  learn list [N]              List recent learning rules (default 10)
  audit                       Run the alignment audit
  health                      Weekly strategic-plan health check (v0.23.6)
  review-prep                 Quarterly strategic-review packet (v0.23.7)
  setup                       Migration-or-clean-install (v0.20+)
  help                        Show this message

HermesAgency wires 7 reliability systems into Hermes:
  1. Supervised learning loop      (pre_llm_call hook)
  2. Autonomy ladder (L1–L5)       (pre_tool_call hook)
  3. Verifier                      (post_tool_call hook)
  4. System Sentinel               (on_session_start/end hooks)
  5. Kanban tracks-link            (Hermes kanban shim)
  6. Send-guard                    (pre_tool_call hook on mail tools)
  7. Audit (weekly alignment)      (scheduled script)

See `/agency systems` for current integration state.
Full docs: https://github.com/ajcrabill/hermes-agency
"""


def handle_agency_command(raw_args: str) -> Optional[str]:
    """Entry point for `/agency <subcommand>` inside Hermes."""
    argv = (raw_args or "").strip().split(None, 1)
    if not argv or argv[0] in ("help", "-h", "--help"):
        return _HELP_TEXT

    sub = argv[0].lower()
    rest = argv[1] if len(argv) > 1 else ""

    try:
        if sub == "status":
            return _cmd_status()
        if sub == "next":
            return _cmd_next()
        if sub == "systems":
            return _cmd_systems()
        if sub == "capture":
            return _cmd_capture(rest)
        if sub == "learn":
            return _cmd_learn(rest)
        if sub == "audit":
            return _cmd_audit()
        if sub == "health":
            return _cmd_health()
        if sub in ("review-prep", "review_prep"):
            return _cmd_review_prep()
        if sub == "setup":
            return _cmd_setup(rest)
        return f"Unknown /agency subcommand: {sub}\n\n{_HELP_TEXT}"
    except Exception as e:
        return f"/agency {sub} failed: {e}"


def _cmd_status() -> str:
    """Compact status: Hermes version, agency version, profile count,
    learning rules count, deployment validity."""
    from _framework import __version__ as agency_version
    from _framework.hermes_engine import detect
    from .context import _agency_home, current_profile_and_role, is_configured

    lines = [f"HermesAgency {agency_version}"]
    home = _agency_home()
    lines.append(f"  AGENCY_HOME: {home}")
    if not home.exists():
        lines.append("  ✗ deployment not initialized")
        return "\n".join(lines)

    # Hermes
    hi = detect()
    if hi.installed:
        lines.append(f"  Hermes: ✓ {hi.version or 'detected'}  ({hi.home})")
    else:
        lines.append("  Hermes: ✗ not detected (you're somehow in a Hermes session though?)")

    # Profile
    profile, role = current_profile_and_role()
    if profile:
        lines.append(f"  primary profile: {profile} ({role})")
    else:
        lines.append("  primary profile: (not configured)")

    # Configured?
    if is_configured():
        lines.append("  setup: ✓ configured")
    else:
        lines.append("  setup: ! not yet configured — run `/agency setup`")

    # Learning rules count
    try:
        from _framework.constants import LEARNING_DB
        if LEARNING_DB.exists():
            import sqlite3
            with sqlite3.connect(LEARNING_DB) as cx:
                n = cx.execute(
                    "SELECT COUNT(*) FROM learning_rules WHERE status='active'"
                ).fetchone()[0]
            lines.append(f"  learning rules: {n} active")
        else:
            lines.append("  learning rules: (DB not initialized)")
    except Exception:
        pass

    return "\n".join(lines)


def _cmd_next() -> str:
    """Actionable next-steps based on deployment state."""
    from .context import is_configured, current_profile_and_role
    from _framework.hermes_engine import detect

    if not detect().installed:
        return ("[BLOCKER] Hermes not detected. (You're seeing this from inside "
                "Hermes though, which is contradictory — please report.)")

    profile, _ = current_profile_and_role()
    if profile is None:
        return ("[BLOCKER] No deployment profile configured.\n"
                "  Run: agency init   (in shell)")

    if not is_configured():
        return ("[SETUP] Deployment not yet configured.\n"
                "  Run: /agency setup   (here, inside Hermes)\n"
                "  This is the migration-or-clean-install interview.")

    return ("✓ Deployment is configured and Hermes is running.\n"
            "  Things you can do here:\n"
            "    /agency status       see the integration state\n"
            "    /agency capture \"...\" capture a correction\n"
            "    /agency audit        run the alignment audit\n"
            "    /agency systems      see which reliability systems are wired")


def _cmd_systems() -> str:
    """The 7-system inventory — same as `agency hermes-patches systems`
    but rendered for the slash command."""
    from .system_inventory import system_inventory

    lines = ["HermesAgency — 7 reliability systems"]
    wired = 0
    for s in system_inventory():
        st = s.get("applied_status", "unknown")
        if st in ("applied", "n/a"):
            wired += 1
            marker = "✓"
        elif st == "not-built":
            marker = "✗"
        else:
            marker = "—"
        lines.append(f"  {marker} {s['name']}")
    lines.append("")
    lines.append(f"  {wired} / {len(system_inventory())} wired")
    lines.append("")
    lines.append("Note: v0.17+ wires via Hermes' plugin API (pre/post_tool_call,")
    lines.append("pre_llm_call, on_session_start/end). v0.16 and earlier used")
    lines.append("text-anchor patches — that approach is deprecated.")
    return "\n".join(lines)


def _cmd_capture(text: str) -> str:
    """Capture a learning correction. Hermes' text comes in raw —
    accept either quoted or unquoted forms."""
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    if not text:
        return "Usage: /agency capture \"<correction text>\""
    try:
        from _framework.learning import capture_correction
        result = capture_correction(
            correction=text,
            source="hermes-session",
            skill_tags=["general", "interactive-chat"],
        )
        msg = f"✓ Captured rule {result.rule_id}: {text[:80]}{'…' if len(text) > 80 else ''}"
        if result.recapture is not None:
            msg += "\n  ⚠ Re-capture detected — the learning loop broke somewhere."
        return msg
    except Exception as e:
        return f"capture failed: {e}"


def _cmd_learn(rest: str) -> str:
    """`/agency learn list [N]` — show recent learning rules."""
    argv = rest.strip().split()
    if not argv or argv[0] != "list":
        return "Usage: /agency learn list [N]"
    try:
        limit = int(argv[1]) if len(argv) > 1 else 10
    except ValueError:
        limit = 10
    try:
        from _framework.constants import LEARNING_DB
        import sqlite3
        if not LEARNING_DB.exists():
            return "(no learning rules yet — capture one with `/agency capture \"...\"`)"
        with sqlite3.connect(LEARNING_DB) as cx:
            cx.row_factory = sqlite3.Row
            rows = cx.execute(
                "SELECT id, correction, is_hard FROM learning_rules "
                "WHERE status='active' "
                "ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        if not rows:
            return "(no active learning rules)"
        out = [f"Most recent {len(rows)} learning rules:"]
        for r in rows:
            mark = " (HARD)" if r["is_hard"] else ""
            preview = r["correction"][:100] + ("…" if len(r["correction"]) > 100 else "")
            out.append(f"  {r['id']}{mark}: {preview}")
        return "\n".join(out)
    except Exception as e:
        return f"learn list failed: {e}"


def _cmd_audit() -> str:
    """Run the alignment audit and return a summary."""
    try:
        from _framework.audit import audit_alignment
        report = audit_alignment.audit_self()
        blocking = report.blocking_findings
        warnings = [f for f in report.findings if not f.is_blocking]
        if not report.findings:
            return f"audit: ✓ clean ({len(report.rules_run)} rules run)"
        out = [f"audit: {len(blocking)} blocking, {len(warnings)} warning(s)"]
        for f in blocking[:5]:
            out.append(f"  ✗ [{f.code}] {f.message}")
        for f in warnings[:5]:
            out.append(f"  ⚠ [{f.code}] {f.message}")
        if len(report.findings) > 10:
            out.append(f"  ... + {len(report.findings) - 10} more")
        out.append("Run `agency audit` in shell for full output.")
        return "\n".join(out)
    except Exception as e:
        return f"audit failed: {e}"


def _cmd_health() -> str:
    """v0.23.6: weekly strategic-plan health check.

    Reads the three-layer Goals.md + goal-tracking DB + firings DB +
    audit findings, and produces a short plain-language summary that
    names drift and proposes pivots. Cadence is intended to be weekly
    but the command lets the Principal pull it manually any time.
    """
    try:
        from _framework.strategic_health import (
            run_health_check, render_report,
        )
        report = run_health_check()
        return render_report(report)
    except Exception as e:
        return f"strategic-plan health check failed: {e}"


def _cmd_review_prep() -> str:
    """v0.23.7: quarterly strategic-review packet.

    Produces the data packet the Principal walks into the
    quarterly review meeting with. The meeting is Principal-driven;
    the CoS prepares.

    Cadence: invoked weekly by the CoS's `quarterly-trigger-check`
    cron — runs the actual packet only on the first Monday of
    Jan / Apr / Jul / Oct. The Principal can also pull manually
    any time.
    """
    try:
        from _framework.strategic_review import (
            produce_review_packet, render_packet,
        )
        packet = produce_review_packet()
        return render_packet(packet)
    except Exception as e:
        return f"strategic-review-prep failed: {e}"


def _cmd_setup(rest: str = "") -> str:
    """Migration-or-clean-install interview. v0.19 ships the real
    flow via the setup state machine."""
    from .setup import handle_setup_command
    return handle_setup_command(rest)


__all__ = ["handle_agency_command"]
