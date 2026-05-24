#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER. Copy to your profile's scripts/ and
# customize. Generic shape; agency-specific logic lives in the copy.
"""
pipeline-watchdog — observability over an agent's outbound pipeline.

Default behavior: scan recent kanban tasks owned by this profile,
flag stale claims + stalled drafts. Emits one event per scan,
emits one heartbeat per run.

Cron cadence: every 15 minutes
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone

from _framework.constants import KANBAN_DB
from _framework.heartbeats import beat
from _framework.sentinel import append_event


STALE_CLAIM_HOURS = 4   # tasks claimed but not finished after this many hours
STALLED_DRAFT_HOURS = 24


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline watchdog")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    findings: list[dict] = []
    try:
        if not KANBAN_DB.exists():
            append_event("pipeline_watchdog_skipped", actor=args.profile,
                         severity="info", payload={"reason": "kanban.db absent"})
            beat(f"{args.profile}-pipeline-watchdog")
            return 0
        c = sqlite3.connect(str(KANBAN_DB))
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT id, status, claim_lock, updated_at FROM tasks "
            "WHERE assignee=? AND status IN ('claimed', 'in_progress')",
            (args.profile,),
        ).fetchall()
        c.close()
    except sqlite3.OperationalError as e:
        append_event("pipeline_watchdog_failed", actor=args.profile,
                     severity="warn", payload={"error": str(e)})
        beat(f"{args.profile}-pipeline-watchdog")
        return 1

    now = datetime.now(timezone.utc)
    for r in rows:
        try:
            updated = datetime.fromisoformat(r["updated_at"])
        except Exception:
            continue
        age_hours = (now - updated).total_seconds() / 3600
        if age_hours > STALE_CLAIM_HOURS:
            findings.append({
                "task_id": r["id"], "status": r["status"],
                "age_hours": round(age_hours, 1),
            })

    if findings:
        for f in findings:
            append_event(
                "pipeline_stale_claim",
                actor=args.profile, target=f["task_id"],
                severity="warn", payload=f,
            )

    beat(f"{args.profile}-pipeline-watchdog")
    return 0


if __name__ == "__main__":
    sys.exit(main())
