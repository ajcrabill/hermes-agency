#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
poll-inbox — fetch new messages from the mailbox; route each through
the CRM reply-matcher and into the kanban for triage.

Transport is operator-configured: Himalaya CLI (IMAP/SMTP), Gmail
OAuth, IMAP, or anything that exposes a list-new-messages interface.
Wire your backend in the TRANSPORT block.
"""

from __future__ import annotations

import argparse
import sys

from _framework.crm import log_reply, match_reply
from _framework.heartbeats import beat
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inbox poll + reply match")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)

    processed = 0
    matched = {1: 0, 2: 0, 3: 0, 4: 0}

    # ── TRANSPORT BLOCK ─────────────────────────────────────────────────
    # Example: replace this loop body with calls to your mail backend.
    #
    #   for msg in your_transport.list_new(limit=args.limit):
    #       m = match_reply(from_email=msg.from_email, thread_id=msg.thread_id)
    #       matched[m.priority] += 1
    #       log_reply(
    #           from_email=msg.from_email,
    #           from_name=msg.from_name,
    #           subject=msg.subject,
    #           snippet=msg.snippet,
    #           thread_id=msg.thread_id,
    #           lead_id=m.lead_id,
    #           contact_id=m.contact_id,
    #           match_priority=m.priority,
    #           sentiment="unknown",   # classifier in a different skill
    #       )
    #       processed += 1
    #       if not m.matched:
    #           # File a kanban task for owner review
    #           ...

    append_event(
        "inbox_polled", actor=args.profile, severity="info",
        payload={"processed": processed,
                 "matched_p1": matched[1], "matched_p2": matched[2],
                 "matched_p3": matched[3], "unmatched_p4": matched[4]},
    )
    beat(f"{args.profile}-poll-inbox")
    return 0


if __name__ == "__main__":
    sys.exit(main())
