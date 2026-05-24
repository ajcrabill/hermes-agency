#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
archive-enforcer — enforces hard archive-rules from the learning corpus
against the inbox.

For each learning rule tagged `archive-rule`, scan recent messages and
archive (or label) any matching ones. Records firings per applied rule.

Cron cadence: every hour during work hours, every 4h overnight.

Generic: the actual mail-transport call depends on which mail backend
the deployment uses (Himalaya, OAuth Gmail, IMAP). Operator wires the
transport in the # TRANSPORT block below.
"""

from __future__ import annotations

import argparse
import sys

from _framework.heartbeats import beat
from _framework.learning import record_firing
from _framework.learning.learning_db import get_db, decode_json_col
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive enforcer")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        # Pull active hard archive-rules
        db = get_db()
        rows = db.execute(
            "SELECT id, correction, skill_tags FROM learning_rules "
            "WHERE status='active' AND is_hard=1 AND skill_tags LIKE '%archive-rule%'"
        ).fetchall()
        db.close()
    except Exception as e:
        append_event("archive_enforcer_failed", actor=args.profile, severity="warn",
                     payload={"error": str(e)})
        beat(f"{args.profile}-archive-enforcer")
        return 1

    rules = [{"id": r["id"], "correction": r["correction"]} for r in rows]
    applied = 0

    # ── TRANSPORT BLOCK: customize per deployment ──────────────────────
    # The framework doesn't ship a default mail transport. Wire your
    # preferred backend here:
    #
    #   from your_transport import list_recent, archive
    #   for msg in list_recent(limit=200):
    #       for rule in rules:
    #           if matches(rule, msg):
    #               if not args.dry_run:
    #                   archive(msg.id)
    #               record_firing(rule_id=rule["id"], skill_tag="archive-enforcer",
    #                             profile=args.profile,
    #                             action_summary=f"archived {msg.id}")
    #               applied += 1
    #               break

    append_event(
        "archive_enforcer_ran", actor=args.profile, severity="info",
        payload={"rules_evaluated": len(rules), "applied": applied,
                 "dry_run": args.dry_run},
    )
    beat(f"{args.profile}-archive-enforcer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
