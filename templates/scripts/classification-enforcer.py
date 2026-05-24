#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
classification-enforcer — applies hard classification rules from the
learning corpus to incoming messages at execution layer.

Different from learning rules at inject-time: those shape the model's
decisions. This is the deterministic gate that overrides the model
when a hard rule applies (e.g. "anything from this domain → always
archive, never draft").
"""

from __future__ import annotations

import argparse
import sys

from _framework.heartbeats import beat
from _framework.learning import record_firing
from _framework.learning.learning_db import get_db
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classification enforcer")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args(argv)

    try:
        db = get_db()
        rules = db.execute(
            "SELECT id, correction, skill_tags FROM learning_rules "
            "WHERE status='active' AND is_hard=1 AND skill_tags LIKE '%classification-rule%'"
        ).fetchall()
        db.close()
    except Exception as e:
        append_event("classification_enforcer_failed", actor=args.profile,
                     severity="warn", payload={"error": str(e)})
        beat(f"{args.profile}-classification-enforcer")
        return 1

    # TRANSPORT BLOCK — wire to your inbox poller.
    # For each freshly-received message, check it against each hard
    # classification rule. If a rule matches, apply its classification
    # (label, route, archive, etc.) and record the firing.

    append_event(
        "classification_enforcer_ran", actor=args.profile, severity="info",
        payload={"rules_loaded": len(rules)},
    )
    beat(f"{args.profile}-classification-enforcer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
