#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
find-candidates — BD prospect identification from news + watchlists.

Reads:  configured signal sources (RSS, news APIs, watchlists)
Writes: candidate records to CRM (status=new) + kanban task per candidate
        for BD's prospect-research skill to qualify

Generic shape: the signal-source plumbing is deployment-specific.
Operator wires their feeds in the SOURCES block.
"""

from __future__ import annotations

import argparse
import sys

from _framework.crm import add_lead, list_leads
from _framework.heartbeats import beat
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find BD candidates from signals")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--max-candidates", type=int, default=20)
    args = parser.parse_args(argv)

    candidates: list[dict] = []
    # ── SOURCES BLOCK: customize per deployment ────────────────────────
    # Examples:
    #   - RSS feeds of industry news
    #   - LinkedIn watchlist (role-change notifications)
    #   - Press-release feeds
    #   - Custom Google Alerts → email → polled by another script
    #
    # For each signal, derive: name, primary_email (or domain),
    # triggering_event (URL + date), reason ("fit because...").
    # Append to `candidates`.

    # Deduplicate against existing CRM leads
    existing = {l["primary_email"] for l in list_leads(limit=1000) if l.get("primary_email")}
    new_count = 0
    for c in candidates[: args.max_candidates]:
        if c.get("primary_email") in existing:
            continue
        add_lead(
            name=c["name"],
            primary_email=c.get("primary_email"),
            status="new",
            source="find-candidates",
            metadata={"triggering_event": c.get("triggering_event", "")},
        )
        new_count += 1

    append_event(
        "find_candidates_ran", actor=args.profile, severity="info",
        payload={"candidates_total": len(candidates), "new_added": new_count},
    )
    beat(f"{args.profile}-find-candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
