#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
follow-up-generator — drafts follow-up messages for stalled prospects.

For each lead flagged by outreach-tracker as needing follow-up, draft
a context-aware follow-up message (in the agency's voice, referencing
the original outreach) and hand to CoS via kanban.
"""

from __future__ import annotations

import argparse
import sys

from _framework.crm import list_leads, find_recent_replies
from _framework.heartbeats import beat
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Follow-up generator")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--max-followups", type=int, default=10,
                        help="Limit per run to avoid flooding CoS queue")
    args = parser.parse_args(argv)

    candidates = []
    for lead in list_leads(status="active"):
        if lead["status"] != "active":
            continue
        replies = find_recent_replies(lead_id=lead["id"], days=14)
        if replies:
            continue   # they replied; not stalled
        candidates.append(lead)
        if len(candidates) >= args.max_followups:
            break

    # For each candidate: generate a draft. The actual drafting logic
    # belongs to the `opportunistic-outreach` or `prospect-research`
    # skill — this script just queues them.
    for lead in candidates:
        append_event(
            "followup_queued", actor=args.profile, target=str(lead["id"]),
            severity="info",
            payload={"lead_name": lead["name"], "status": lead["status"]},
        )

    beat(f"{args.profile}-follow-up-generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
