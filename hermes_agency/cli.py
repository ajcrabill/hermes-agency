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


def cmd_audit(_args: argparse.Namespace) -> int:
    """Run the framework audit (Week 4 build target)."""
    print("agency audit: not yet implemented (Week 4 of v0.1 build).")
    return 0


def cmd_capture(_args: argparse.Namespace) -> int:
    """Capture a correction interactively (Week 2 build target)."""
    print("agency capture: not yet implemented (Week 2 of v0.1 build).")
    return 0


def cmd_learn(args: argparse.Namespace) -> int:
    """Learning subsystem queries (Week 2 build target)."""
    print(f"agency learn {args.action}: not yet implemented (Week 2 of v0.1 build).")
    return 0


def cmd_promote(_args: argparse.Namespace) -> int:
    """Force-promote a skill (Week 3 build target)."""
    print("agency promote: not yet implemented (Week 3 of v0.1 build).")
    return 0


def cmd_demote(_args: argparse.Namespace) -> int:
    """Force-demote a skill (Week 3 build target)."""
    print("agency demote: not yet implemented (Week 3 of v0.1 build).")
    return 0


def cmd_events(_args: argparse.Namespace) -> int:
    """Live events feed (Week 4 build target)."""
    print("agency events: not yet implemented (Week 4 of v0.1 build).")
    return 0


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
    p_audit.set_defaults(func=cmd_audit)

    # capture
    p_capture = sub.add_parser("capture", help="Capture a learning correction")
    p_capture.add_argument("text", nargs="?", help="The correction text")
    p_capture.set_defaults(func=cmd_capture)

    # learn (subcommands)
    p_learn = sub.add_parser("learn", help="Learning subsystem queries")
    p_learn.add_argument("action", choices=["list", "show"])
    p_learn.add_argument("rule_id", nargs="?")
    p_learn.set_defaults(func=cmd_learn)

    # promote / demote
    p_promote = sub.add_parser("promote", help="Force-promote a skill (gated by audit)")
    p_promote.add_argument("skill")
    p_promote.set_defaults(func=cmd_promote)

    p_demote = sub.add_parser("demote", help="Force-demote a skill")
    p_demote.add_argument("skill")
    p_demote.add_argument("--reason", default="manual")
    p_demote.set_defaults(func=cmd_demote)

    # events
    p_events = sub.add_parser("events", help="Live events feed")
    p_events.add_argument("--tail", action="store_true")
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
