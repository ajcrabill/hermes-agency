#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
outreach-tracker — verifies sent outbound emails landed + detects
bounces + schedules follow-ups.

For each sent_thread without a confirmed delivery, check the mail
backend. For each delivered message older than the follow-up
threshold without a reply, file a follow-up kanban task.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from _framework.crm import find_recent_replies, list_leads
from _framework.heartbeats import beat
from _framework.sentinel import append_event


FOLLOW_UP_DAYS_DEFAULT = 7


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Outreach tracker")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--follow-up-days", type=int, default=FOLLOW_UP_DAYS_DEFAULT)
    args = parser.parse_args(argv)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.follow_up_days)
    needs_followup: list[dict] = []

    for lead in list_leads(status="active"):
        last_outbound = lead.get("last_touch_primary") or lead.get("last_touch_secondary")
        if not last_outbound:
            continue
        try:
            last_dt = datetime.fromisoformat(last_outbound)
        except Exception:
            continue
        if last_dt > cutoff:
            continue   # not yet ready for follow-up
        recent_replies = find_recent_replies(lead_id=lead["id"], days=args.follow_up_days)
        if recent_replies:
            continue   # they replied; the reply matcher will handle status
        needs_followup.append({
            "lead_id": lead["id"], "name": lead["name"],
            "days_since": (datetime.now(timezone.utc) - last_dt).days,
        })

    for item in needs_followup:
        append_event(
            "outreach_followup_due", actor=args.profile, target=str(item["lead_id"]),
            severity="info", payload=item,
        )

    beat(f"{args.profile}-outreach-tracker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
