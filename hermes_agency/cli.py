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
    """Stub: full wizard ships in Week 6. Today it copies the template and prints next steps."""
    from _framework.constants import (
        AGENCY_HOME,
        DEPLOYMENT_YAML,
        TEMPLATES_DIR,
    )

    if not AGENCY_HOME.exists():
        AGENCY_HOME.mkdir(parents=True)
    template = TEMPLATES_DIR / "deployment.yaml.template"
    if DEPLOYMENT_YAML.exists() and not args.force:
        print(f"deployment.yaml already exists at {DEPLOYMENT_YAML}.")
        print("Pass --force to overwrite.")
        return 1
    DEPLOYMENT_YAML.write_text(template.read_text())
    print(f"Wrote {DEPLOYMENT_YAML} from template.")
    print()
    print(f"Tier {args.tier} interactive wizard is not yet implemented (Week 6 deliverable).")
    print("For now, open deployment.yaml in an editor and replace {{PLACEHOLDERS}} by hand.")
    print(f"Then run: agency status")
    return 0


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
    """Framework version bump (Week 6 build target)."""
    print("agency upgrade: not yet implemented (Week 6 of v0.1 build).")
    return 0


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
