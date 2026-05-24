"""
HermesAgency CLI — `agency <command> [...]`.

Commands (per spec §11.3):
  agency status               quick health summary
  agency init [--tier 1|2|3]  the wizard
  agency upgrade              framework version bump
  agency audit                run audit-alignment.py
  agency capture "..."        interactive correction capture
  agency promote <skill>      force-promote (gated by audit)
  agency demote <skill>       force-demote
  agency events --tail        live events feed
  agency learn list           list learning rules
  agency learn show <id>      show one rule + firings

Each subcommand delegates into a framework module — the CLI itself
holds no domain logic. New commands plug in via the subparsers
registry.

This is a skeleton; subcommands fill in as the build progresses
(Week 1 ships status/init/audit/manifest-validate stubs; Week 2 adds
capture/learn; Week 3 adds promote/demote; Week 4 adds events; Week 6
adds the wizard interactive flow).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _framework import __version__
from _framework.constants import AGENCY_HOME, DEPLOYMENT_YAML


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"hermes-agency {__version__}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Quick health check — manifest valid? state dirs present? agents alive?"""
    from _framework.manifest import validate

    print(f"HermesAgency {__version__}")
    print(f"  AGENCY_HOME: {AGENCY_HOME}")
    if not AGENCY_HOME.exists():
        print("  ✗ AGENCY_HOME does not exist. Run ./install.sh first.")
        return 1

    print(f"  deployment.yaml: {DEPLOYMENT_YAML}")
    result = validate(DEPLOYMENT_YAML)
    if not result.findings:
        print("    ✓ valid")
    else:
        n_err = len(result.errors)
        n_warn = len(result.warnings)
        print(f"    {n_err} error(s), {n_warn} warning(s)")
        if args.verbose:
            for f in result.findings:
                print(f"      {f}")
    return 0 if result.ok else 1


def cmd_init(args: argparse.Namespace) -> int:
    """Three-tier interactive wizard."""
    from _framework.ops.init import run_wizard
    return run_wizard(tier=args.tier, force=args.force)


def cmd_manifest_validate(args: argparse.Namespace) -> int:
    """Direct passthrough to the manifest validator."""
    from _framework.manifest import main as _main
    sys.argv = ["agency-manifest-validate"]
    if args.path:
        sys.argv.append(args.path)
    if args.quiet:
        sys.argv.append("--quiet")
    return _main()


def cmd_audit(args: argparse.Namespace) -> int:
    """Run the framework + deployment audit."""
    from _framework.audit import audit_alignment

    if args.self_audit:
        report = audit_alignment.audit_self()
    elif args.skill:
        if not args.profile:
            print("--skill requires --profile", file=sys.stderr)
            return 2
        report = audit_alignment.audit_skill(skill=args.skill, profile=args.profile, strict=args.strict)
    elif args.profile:
        report = audit_alignment.audit_profile(profile=args.profile, strict=args.strict)
    else:
        report = audit_alignment.audit_deployment(strict=args.strict)

    print(report.render())
    return 0 if report.passed else 1


def cmd_capture(args: argparse.Namespace) -> int:
    """Capture a learning correction into the corpus."""
    from _framework.learning import capture_correction
    text = args.text
    if not text:
        print("Reading correction from stdin (Ctrl-D to finish):")
        text = sys.stdin.read().strip()
    if not text:
        print("error: no correction text provided", file=sys.stderr)
        return 1

    skill_tags = args.skill or ["general"]
    role_tags = args.role or []
    voice_tags = args.voice or []
    source = args.source or "cli:agency-capture"

    try:
        result = capture_correction(
            correction=text,
            source=source,
            skill_tags=skill_tags,
            role_tags=role_tags,
            voice_tags=voice_tags,
            is_hard=args.hard,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Captured rule {result.rule_id}")
    print(f"  skill_tags: {', '.join(result.skill_tags)}")
    if result.role_tags:
        print(f"  role_tags:  {', '.join(result.role_tags)}")
    if result.voice_tags:
        print(f"  voice_tags: {', '.join(result.voice_tags)}")
    if result.is_hard:
        print(f"  is_hard:    true")
    if result.tag_issues:
        print("  tag warnings:")
        for issue in result.tag_issues:
            print(f"    - {issue}")
    if result.recapture:
        print()
        print(f"⚠ RECAPTURE DETECTED")
        print(f"  similar to: {result.recapture.similar_to}")
        print(f"  similarity: {result.recapture.similarity:.3f}")
        print(f"  This is a system-failure flag — the loop broke somewhere upstream.")
    return 0


def cmd_learn(args: argparse.Namespace) -> int:
    """Learning subsystem queries: list / show."""
    from _framework.learning.learning_db import get_db, decode_json_col, row_to_rule

    if args.action == "list":
        db = get_db()
        try:
            limit = args.limit if args.limit else 50
            rows = db.execute(
                "SELECT * FROM learning_rules WHERE status='active' "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            db.close()
        if not rows:
            print("No active learning rules yet. Capture one with `agency capture \"...\"`")
            return 0
        for r in rows:
            d = row_to_rule(r)
            tags = ", ".join(d["skill_tags"])
            hard = " (HARD)" if d.get("is_hard") else ""
            print(f"{d['id']}{hard}  {d['correction'][:80]}")
            print(f"          skills: {tags}")
            if d.get("role_tags"):
                print(f"          roles:  {', '.join(d['role_tags'])}")
        return 0

    if args.action == "show":
        if not args.rule_id:
            print("error: agency learn show <rule_id>", file=sys.stderr)
            return 1
        db = get_db()
        try:
            row = db.execute("SELECT * FROM learning_rules WHERE id=?", (args.rule_id,)).fetchone()
            if not row:
                print(f"No rule with id {args.rule_id}", file=sys.stderr)
                return 1
            d = row_to_rule(row)
            fire_rows = db.execute(
                "SELECT * FROM firings WHERE rule_id=? ORDER BY created_at DESC LIMIT 20",
                (args.rule_id,),
            ).fetchall()
        finally:
            db.close()

        print(f"rule {d['id']}")
        print(f"  correction:  {d['correction']}")
        print(f"  source:      {d['source']}")
        print(f"  skill_tags:  {', '.join(d['skill_tags'])}")
        if d.get("role_tags"):
            print(f"  role_tags:   {', '.join(d['role_tags'])}")
        if d.get("voice_tags"):
            print(f"  voice_tags:  {', '.join(d['voice_tags'])}")
        print(f"  is_hard:     {bool(d.get('is_hard'))}")
        print(f"  status:      {d['status']}")
        print(f"  created_at:  {d['created_at']}")
        if d.get("notes"):
            print(f"  notes:       {d['notes']}")
        print(f"  firings ({len(fire_rows)} most recent):")
        for f in fire_rows:
            override = " (override-attempt)" if f["was_overridden"] else ""
            print(f"    {f['created_at']}  {f['profile']}:{f['skill_tag']}{override}")
        return 0

    print(f"unknown action: {args.action}", file=sys.stderr)
    return 1


def cmd_promote(args: argparse.Namespace) -> int:
    """Force-promote a skill (still goes through the graduation gate)."""
    from _framework.autonomy import promote
    skill = args.skill
    profile = args.profile or "default"
    result = promote(skill=skill, profile=profile, reason=args.reason or "cli-promote")
    if result.blocked:
        print(f"REFUSED — {result.blocker}: {result.reason}")
        return 1
    if result.from_level == result.to_level:
        print(f"{profile}:{skill} stays at L{result.from_level} ({result.reason})")
        return 0
    print(f"{profile}:{skill} L{result.from_level} → L{result.to_level} ({result.reason})")
    return 0


def cmd_demote(args: argparse.Namespace) -> int:
    """Force-demote a skill (no gate; demotion is always allowed)."""
    from _framework.autonomy import demote
    skill = args.skill
    profile = args.profile or "default"
    result = demote(skill=skill, profile=profile, reason=args.reason)
    print(f"{profile}:{skill} L{result.from_level} → L{result.to_level} ({result.reason})")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    """Recent events feed (or --tail to stream)."""
    from _framework.sentinel import recent_events
    import time as _time

    if args.tail:
        # Simple polling tail: print new rows every 2s for `args.duration`
        # seconds (or until interrupted).
        seen_ids: set[int] = set()
        deadline = _time.time() + (args.duration or 60)
        try:
            while _time.time() < deadline:
                rows = recent_events(limit=args.limit, minutes=args.minutes)
                for r in reversed(rows):
                    rid = int(r["id"])
                    if rid in seen_ids:
                        continue
                    seen_ids.add(rid)
                    _print_event(r)
                _time.sleep(2)
        except KeyboardInterrupt:
            pass
        return 0

    rows = recent_events(limit=args.limit, minutes=args.minutes, kind=args.kind, actor=args.actor)
    if not rows:
        print("(no events)")
        return 0
    for r in rows:
        _print_event(r)
    return 0


def _print_event(r: dict) -> None:
    sev = r.get("severity") or "info"
    actor = r.get("actor") or "-"
    target = r.get("target") or "-"
    print(f"{r['ts']}  [{sev:8s}] {r['kind']:30s}  {actor:10s} → {target}")


def cmd_upgrade(_args: argparse.Namespace) -> int:
    """Framework version bump.

    v0.1: prints current version and the recommended manual upgrade
    flow. Full automated migration (schema bumps, manifest evolution)
    ships in v0.2.
    """
    from _framework.constants import FRAMEWORK_VERSION_LOCK
    print(f"hermes-agency {__version__}")
    if FRAMEWORK_VERSION_LOCK.exists():
        pinned = FRAMEWORK_VERSION_LOCK.read_text(encoding="utf-8").strip()
        print(f"  deployment pinned at: {pinned}")
    print("\nv0.1 upgrade flow (manual):")
    print("  1. cd ~/HermesAgency && git pull")
    print("  2. ./install.sh   # idempotent; preserves your deployment")
    print("  3. agency manifest-validate   # confirm schema still passes")
    print("  4. agency audit --self        # confirm no framework-level findings")
    print("\nAutomated migration is a v0.2 deliverable.")
    return 0


def cmd_hermes_patches(args: argparse.Namespace) -> int:
    """Apply / status / list Hermes integration patches."""
    from _framework.hermes_patches import apply_all, check_status, list_patches

    if args.action == "list":
        for p in list_patches():
            print(f"  {p.id}: {p.description}")
        return 0
    if args.action == "apply":
        statuses = apply_all(dry_run=args.dry_run)
    else:
        statuses = check_status()
    for s in statuses:
        marker = {
            "applied": "✓", "unapplied": "—",
            "anchor-missing": "⚠", "target-missing": "?",
        }.get(s.status, "·")
        print(f"  {marker} {s.id:30s} [{s.status}]  {s.target_path or '(no target)'}")
    return 0 if all(s.status in ("applied", "target-missing") for s in statuses) else 1


def cmd_cron(args: argparse.Namespace) -> int:
    """Sync per-profile cron jobs into Hermes' scheduler."""
    from _framework.cron import list_jobs, sync_cron_jobs

    if args.action == "list":
        jobs = list_jobs(profile=args.profile)
        if not jobs:
            print("(no per-profile jobs.json files found)")
            return 0
        for j in jobs:
            profile = j.get("_profile", "?")
            sched = j.get("schedule", {})
            print(f"  {profile:12s} {j.get('name', '?'):30s} {sched}")
        return 0

    # sync
    summary = sync_cron_jobs(dry_run=args.dry_run)
    print(f"Target: {summary['target']}")
    print(f"  operator jobs preserved: {summary['operator_jobs']}")
    print(f"  framework jobs before:   {summary['framework_jobs_before']}")
    print(f"  framework jobs after:    {summary['framework_jobs_after']}")
    if summary.get("dry_run"):
        print("  (dry-run — no changes written)")
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    """Read or append to operational-state.md / conversation-journal.md."""
    from _framework.state import (
        append_to_section, read_conversation_journal, read_operational_state,
    )
    from _framework.constants import CONVERSATION_JOURNAL_MD, OPERATIONAL_STATE_MD

    path = OPERATIONAL_STATE_MD if args.file == "operational" else CONVERSATION_JOURNAL_MD

    if args.action == "read":
        text = read_operational_state() if args.file == "operational" else read_conversation_journal()
        print(text or f"(no content at {path})")
        return 0

    # append
    if not args.section:
        print("--section required for append", file=sys.stderr)
        return 2
    body = args.body
    if not body:
        print("Reading body from stdin (Ctrl-D to finish):")
        body = sys.stdin.read().strip()
    if not body:
        print("error: no body provided", file=sys.stderr)
        return 1
    append_to_section(path, args.section, body, actor="cli")
    print(f"Appended to '{args.section}' in {path.name}")
    return 0


def cmd_heartbeat(args: argparse.Namespace) -> int:
    """Emit a heartbeat or query liveness."""
    from _framework.heartbeats import beat, recent, stale_components

    if args.action == "beat":
        if not args.component:
            print("--component required for beat", file=sys.stderr)
            return 2
        beat(args.component)
        print(f"beat: {args.component}")
        return 0

    if args.action == "stale":
        stale = stale_components()
        if not stale:
            print("All tracked components within expected cadence.")
            return 0
        for s in stale:
            print(f"  ⚠ {s['component']:30s} last seen {s['age_seconds']}s ago "
                  f"(expected {s['expected_seconds']}s)")
        return 1

    # list
    rows = recent(limit=20)
    if not rows:
        print("(no heartbeats yet)")
        return 0
    for r in rows:
        print(f"  {r['ts']}  {r['component']}")
    return 0


def cmd_integrations(args: argparse.Namespace) -> int:
    """Configure optional integrations (currently: google-drive)."""
    if args.integration == "google-drive":
        if args.action == "status":
            from _framework.integrations.google_drive import is_configured
            if not args.profile:
                print("--profile required", file=sys.stderr)
                return 2
            ok = is_configured(args.profile)
            state = "configured" if ok else "not configured"
            print(f"google-drive for profile '{args.profile}': {state}")
            return 0 if ok else 1
        if args.action == "setup":
            if not args.profile or not args.client_secret:
                print("--profile and --client-secret required", file=sys.stderr)
                return 2
            from _framework.integrations.google_drive import setup_interactive
            try:
                setup_interactive(args.profile, args.client_secret)
            except RuntimeError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            return 0
    print(f"unknown integration: {args.integration}", file=sys.stderr)
    return 2


def cmd_migrate(args: argparse.Namespace) -> int:
    """Plan or apply a migration from a prior deployment (v7 currently)."""
    if args.source != "v7":
        print(f"unknown migration source: {args.source}", file=sys.stderr)
        return 2

    from _framework.migration import (
        plan_v7_learning_migration, apply_v7_learning_migration,
    )

    try:
        plan = plan_v7_learning_migration(args.from_path)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(plan.summary())
    print()

    if plan.to_migrate:
        print(f"Sample of {min(5, len(plan.to_migrate))} rules to migrate:")
        for t in plan.to_migrate[:5]:
            mark = " (HARD)" if t.is_hard else ""
            tags = ", ".join(t.skill_tags) if t.skill_tags else "(no tags)"
            print(f"  · {t.v7_id}{mark}  [{tags}]  {t.correction_preview}")

    if args.action == "plan":
        print()
        print("Plan only. Re-run with `apply` to write to HermesAgency.")
        return 0

    # apply
    print()
    result = apply_v7_learning_migration(plan)
    print(result.summary())
    if result.failures:
        print()
        print("Failures:")
        for f in result.failures[:10]:
            print(f"  · {f.v7_id}  {f.reason}")
    return 0 if result.failed == 0 else 1


def cmd_goals(args: argparse.Namespace) -> int:
    """Show / add / refine / smart-check entries in Goals.md."""
    from _framework.constants import GOALS_MD
    from _framework.goals import (
        read_goals, add_annual_goal, replace_annual_goal,
        add_active_project, smart_check,
    )

    if args.action == "show":
        if not GOALS_MD.exists():
            print(f"(no Goals.md yet at {GOALS_MD} — run `agency init --tier 3`)")
            return 0
        print(GOALS_MD.read_text(encoding="utf-8"))
        return 0

    if args.action == "smart-check":
        if not args.text:
            print("error: --text required for smart-check", file=sys.stderr)
            return 2
        v = smart_check(args.text)
        print(f"Goal: {args.text}\n")
        print(v.render())
        print(f"\n  Overall: {'SMART ✓' if v.is_smart else 'not yet SMART ✗'}")
        return 0 if v.is_smart else 1

    if args.action == "add":
        if not args.text:
            print("error: --text required for add", file=sys.stderr)
            return 2
        if args.smart:
            v = smart_check(args.text)
            if not v.is_smart:
                print("Refusing to add — goal isn't SMART yet:\n")
                print(v.render())
                print("\n  Drop --smart to add anyway.")
                return 1
        add_annual_goal(args.text, interim=args.interim or [])
        print(f"Added annual goal to {GOALS_MD}")
        return 0

    if args.action == "replace":
        if args.index is None or not args.text:
            print("error: --index and --text required for replace", file=sys.stderr)
            return 2
        try:
            replace_annual_goal(args.index, args.text, interim=args.interim or [])
        except IndexError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"Replaced goal #{args.index} in {GOALS_MD}")
        return 0

    if args.action == "add-project":
        if not args.text:
            print("error: --text required for add-project", file=sys.stderr)
            return 2
        add_active_project(args.text, details=args.interim or [])
        print(f"Added active project to {GOALS_MD}")
        return 0

    if args.action == "track":
        # Define a metric for tracking progress
        from _framework.goals import define_metric
        if not args.metric_name or not args.text:
            print("error: --metric and --text (the goal text) required for track",
                  file=sys.stderr)
            return 2
        mid = define_metric(
            goal_text=args.text,
            metric_name=args.metric_name,
            measurement_type=args.measurement_type or "counter",
            unit=args.unit or "",
            target_value=args.target,
            target_at=args.target_at,
            data_source=args.data_source or "manual",
        )
        print(f"Defined metric {args.metric_name} (id={mid}) for goal: {args.text[:60]}")
        return 0

    if args.action == "observe":
        from _framework.goals import record_observation, list_metrics
        if args.metric_name and not args.metric_id:
            metrics = [m for m in list_metrics() if m.metric_name == args.metric_name]
            if not metrics:
                print(f"error: no metric named {args.metric_name!r}", file=sys.stderr)
                return 1
            if len(metrics) > 1:
                print(f"error: multiple metrics named {args.metric_name!r}; pass --metric-id",
                      file=sys.stderr)
                return 1
            args.metric_id = metrics[0].id
        if args.metric_id is None or args.value is None:
            print("error: --metric-id (or --metric) and --value required", file=sys.stderr)
            return 2
        record_observation(metric_id=args.metric_id, value=args.value,
                            note=args.note or "")
        print(f"Recorded value {args.value} for metric id={args.metric_id}")
        return 0

    if args.action == "status":
        from _framework.goals import weekly_status_report
        report = weekly_status_report()
        print(f"Goal tracking status — {report['total_metrics']} metrics:")
        print(f"  ✓ on-track:  {report['on_track']}")
        print(f"  ⚠ at-risk:   {report['at_risk']}")
        print(f"  ✗ missed:    {report['missed']}")
        print(f"  ★ done:      {report['done']}")
        print(f"  · no-data:   {report['no_data']}")
        print()
        # Show at-risk + missed first
        priority = ("missed", "at-risk")
        sorted_metrics = sorted(
            report["metrics"],
            key=lambda s: (s["status"] not in priority, s.get("metric_name", "")),
        )
        for s in sorted_metrics:
            marker = {
                "on-track": "✓", "at-risk": "⚠", "missed": "✗",
                "done": "★", "no-data": "·", "in-progress": "→",
                "no-target": "·",
            }.get(s["status"], "?")
            print(f"  {marker} [{s['status']:8s}] {s.get('metric_name', '?')}: {s.get('reason', '')}")
        return 0

    if args.action == "sync-milestones":
        from _framework.goals import sync_milestones_from_goals_md
        n = sync_milestones_from_goals_md()
        print(f"Synced {n} milestone(s) from Goals.md")
        return 0

    print(f"unknown action: {args.action}", file=sys.stderr)
    return 2


def cmd_panel(args: argparse.Namespace) -> int:
    """Run the read-only control panel."""
    try:
        from _framework.ops.control_panel import main as _panel_main
    except SystemExit as e:
        # aiohttp not installed → re-raise the friendly message
        print(str(e), file=sys.stderr)
        return 1
    import sys as _sys
    saved = _sys.argv
    _sys.argv = ["agency-panel"]
    if args.port:
        _sys.argv.extend(["--port", str(args.port)])
    if args.host:
        _sys.argv.extend(["--host", args.host])
    try:
        return _panel_main()
    finally:
        _sys.argv = saved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agency",
        description=f"HermesAgency {__version__} — multi-agent framework for small agencies.",
    )
    parser.add_argument("-V", "--version", action="store_true", help="Print version and exit.")
    sub = parser.add_subparsers(dest="command")

    # status
    p_status = sub.add_parser("status", help="Quick health summary")
    p_status.add_argument("-v", "--verbose", action="store_true")
    p_status.set_defaults(func=cmd_status)

    # init
    p_init = sub.add_parser("init", help="Provision a deployment (interactive wizard)")
    p_init.add_argument("--tier", type=int, choices=[1, 2, 3], default=1)
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    # manifest-validate (low-level)
    p_mv = sub.add_parser("manifest-validate", help="Validate deployment.yaml")
    p_mv.add_argument("path", nargs="?")
    p_mv.add_argument("-q", "--quiet", action="store_true")
    p_mv.set_defaults(func=cmd_manifest_validate)

    # audit
    p_audit = sub.add_parser("audit", help="Run audit-alignment.py")
    p_audit.add_argument("--skill", help="Audit one skill (requires --profile)")
    p_audit.add_argument("--profile", help="Audit one profile")
    p_audit.add_argument("--strict", action="store_true", help="ALWAYS_BLOCK findings only (graduation-gate mode)")
    p_audit.add_argument("--self", dest="self_audit", action="store_true", help="Audit the framework itself")
    p_audit.set_defaults(func=cmd_audit)

    # capture
    p_capture = sub.add_parser("capture", help="Capture a learning correction")
    p_capture.add_argument("text", nargs="?", help="The correction text (stdin if omitted)")
    p_capture.add_argument("--skill", action="append", help="Skill tag (repeatable; defaults to 'general')")
    p_capture.add_argument("--role", action="append", help="Role tag (repeatable)")
    p_capture.add_argument("--voice", action="append", help="Voice tag (repeatable)")
    p_capture.add_argument("--source", help="Where this correction came from (default: cli:agency-capture)")
    p_capture.add_argument("--hard", action="store_true", help="Mark as a hard rule (deterministically checkable)")
    p_capture.set_defaults(func=cmd_capture)

    # learn (subcommands)
    p_learn = sub.add_parser("learn", help="Learning subsystem queries")
    p_learn.add_argument("action", choices=["list", "show"])
    p_learn.add_argument("rule_id", nargs="?")
    p_learn.add_argument("--limit", type=int, default=50)
    p_learn.set_defaults(func=cmd_learn)

    # promote / demote
    p_promote = sub.add_parser("promote", help="Force-promote a skill (gated by audit)")
    p_promote.add_argument("skill")
    p_promote.add_argument("--profile", required=True, help="Profile id (e.g. loriah)")
    p_promote.add_argument("--reason", default="cli-promote")
    p_promote.set_defaults(func=cmd_promote)

    p_demote = sub.add_parser("demote", help="Force-demote a skill")
    p_demote.add_argument("skill")
    p_demote.add_argument("--profile", required=True, help="Profile id (e.g. loriah)")
    p_demote.add_argument("--reason", default="manual")
    p_demote.set_defaults(func=cmd_demote)

    # events
    p_events = sub.add_parser("events", help="Recent events feed (or --tail to stream)")
    p_events.add_argument("--tail", action="store_true", help="Stream new events as they arrive")
    p_events.add_argument("--duration", type=int, default=60, help="Tail mode: stop after N seconds (default 60)")
    p_events.add_argument("--limit", type=int, default=50, help="Max rows per fetch (default 50)")
    p_events.add_argument("--minutes", type=int, default=60, help="Lookback window in minutes (default 60)")
    p_events.add_argument("--kind", help="Filter by event kind")
    p_events.add_argument("--actor", help="Filter by actor")
    p_events.set_defaults(func=cmd_events)

    # upgrade
    p_upgrade = sub.add_parser("upgrade", help="Framework version bump")
    p_upgrade.set_defaults(func=cmd_upgrade)

    # panel (control panel)
    p_panel = sub.add_parser("panel", help="Run the read-only control panel at localhost:9118")
    p_panel.add_argument("--port", type=int, default=None)
    p_panel.add_argument("--host", default=None)
    p_panel.set_defaults(func=cmd_panel)

    # hermes-patches
    p_patches = sub.add_parser(
        "hermes-patches",
        help="Apply/check the Hermes integration patches (injection, etc.)",
    )
    p_patches.add_argument("action", choices=["apply", "status", "list"], default="status", nargs="?")
    p_patches.add_argument("--dry-run", action="store_true")
    p_patches.set_defaults(func=cmd_hermes_patches)

    # cron sync
    p_cron = sub.add_parser("cron", help="Sync per-profile cron jobs into Hermes' scheduler")
    p_cron.add_argument("action", choices=["sync", "list"], default="list", nargs="?")
    p_cron.add_argument("--profile", help="Limit to one profile")
    p_cron.add_argument("--dry-run", action="store_true")
    p_cron.set_defaults(func=cmd_cron)

    # state-vault
    p_state = sub.add_parser(
        "state",
        help="Read/append operational-state.md and conversation-journal.md",
    )
    p_state.add_argument("action", choices=["read", "append"], default="read", nargs="?")
    p_state.add_argument("--file", choices=["operational", "journal"], default="operational")
    p_state.add_argument("--section", help="(append) section name")
    p_state.add_argument("--body", help="(append) body text (stdin if omitted)")
    p_state.set_defaults(func=cmd_state)

    # heartbeat
    p_heart = sub.add_parser("heartbeat", help="Emit a heartbeat or query liveness")
    p_heart.add_argument("action", choices=["beat", "list", "stale"], default="list", nargs="?")
    p_heart.add_argument("--component", help="(beat) component name")
    p_heart.set_defaults(func=cmd_heartbeat)

    # integrations
    p_int = sub.add_parser("integrations", help="Configure optional integrations")
    p_int.add_argument("integration", choices=["google-drive"])
    p_int.add_argument("action", choices=["setup", "status"])
    p_int.add_argument("--profile", help="Profile to configure")
    p_int.add_argument("--client-secret", help="Path to OAuth client_secret.json")
    p_int.set_defaults(func=cmd_integrations)

    # goals
    p_goals = sub.add_parser(
        "goals",
        help="Show/add/refine Goals.md + SMART-check + tracking",
    )
    p_goals.add_argument(
        "action",
        choices=[
            "show", "smart-check", "add", "replace", "add-project",
            "track", "observe", "status", "sync-milestones",
        ],
        default="show",
        nargs="?",
    )
    p_goals.add_argument("--text", help="Goal or project text")
    p_goals.add_argument("--index", type=int, help="(replace) 0-based index")
    p_goals.add_argument(
        "--interim", action="append",
        help="Interim milestone bullet (repeatable)",
    )
    p_goals.add_argument(
        "--smart", action="store_true",
        help="(add) refuse if the text fails SMART criteria",
    )
    # Tracking arguments
    p_goals.add_argument(
        "--metric", dest="metric_name",
        help="(track / observe) metric name",
    )
    p_goals.add_argument(
        "--measurement-type", dest="measurement_type",
        choices=["counter", "gauge", "percentage", "binary"],
        help="(track) measurement_type",
    )
    p_goals.add_argument("--unit", help="(track) unit string (clients / USD / %)")
    p_goals.add_argument("--target", type=float, help="(track) target value")
    p_goals.add_argument("--target-at", help="(track) target deadline ISO date")
    p_goals.add_argument("--data-source", help="(track) data source description")
    p_goals.add_argument("--metric-id", type=int, help="(observe) metric id")
    p_goals.add_argument("--value", type=float, help="(observe) observed value")
    p_goals.add_argument("--note", help="(observe) note")
    p_goals.set_defaults(func=cmd_goals)

    # migrate
    p_migrate = sub.add_parser(
        "migrate",
        help="Migrate from a prior deployment (v7 learning corpus + more)",
    )
    p_migrate.add_argument(
        "source", choices=["v7"],
        help="Migration source (v7 = legacy Hermes/Loriah deployment)",
    )
    p_migrate.add_argument(
        "action", choices=["plan", "apply"], default="plan", nargs="?",
        help="plan (dry-run report) or apply (write to HermesAgency)",
    )
    p_migrate.add_argument(
        "--from", dest="from_path",
        default="~/.hermes/context/loriah/Admin/loriah.db",
        help="Source v7 database path",
    )
    p_migrate.set_defaults(func=cmd_migrate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
