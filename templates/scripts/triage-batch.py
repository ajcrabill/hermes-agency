#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
triage-batch — render the queued triage summary into one consolidated
draft for {{OWNER}}, then hand to send-orchestrator.

Default behavior: pull kanban tasks assigned to {{OWNER}} that are
ready since the last batch cycle, group by tenant/priority, render
as markdown, save to drafts dir for CoS to send.

Cron cadence: 3x daily (typically 6am, 1pm, 8pm local)
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _framework.constants import AGENCY_HOME, KANBAN_DB
from _framework.heartbeats import beat
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage batch renderer")
    parser.add_argument("--profile", required=True, help="The CoS profile")
    parser.add_argument("--owner-handle", required=True, help="The principal's kanban handle")
    parser.add_argument("--window-hours", type=int, default=8,
                        help="How far back to include (default 8h)")
    args = parser.parse_args(argv)

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=args.window_hours)).isoformat()
    out_dir = AGENCY_HOME / "_health" / "triage-batches"
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_file = out_dir / f"{datetime.now().strftime('%Y-%m-%dT%H')}.md"

    try:
        c = sqlite3.connect(str(KANBAN_DB))
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM tasks WHERE assignee=? AND created_at >= ? "
            "ORDER BY priority DESC, created_at ASC",
            (args.owner_handle, cutoff),
        ).fetchall()
        c.close()
    except Exception as e:
        append_event("triage_batch_failed", actor=args.profile, severity="warn",
                     payload={"error": str(e)})
        beat(f"{args.profile}-triage-batch")
        return 1

    lines = [
        f"# Triage batch — {datetime.now().isoformat(timespec='minutes')}",
        f"",
        f"Items ready for review in the last {args.window_hours}h:",
        f"",
    ]
    for r in rows:
        title = r["title"] if "title" in r.keys() else "(no title)"
        tenant = r["tenant"] if "tenant" in r.keys() else "-"
        lines.append(f"- **[{tenant}]** {title}  (`{r['id']}`)")
    batch_file.write_text("\n".join(lines), encoding="utf-8")

    append_event(
        "triage_batch_rendered", actor=args.profile, severity="info",
        payload={"path": str(batch_file), "items": len(rows)},
    )
    beat(f"{args.profile}-triage-batch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
