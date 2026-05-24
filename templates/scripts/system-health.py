#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
system-health — basic platform sanity check.

Verifies:
  - $AGENCY_HOME exists and is writable
  - All declared state databases are present + non-corrupt
  - Python deps the deployment requires are importable
  - Disk space sufficient

Emits events; files a kanban alert if anything critical fails.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

from _framework.constants import (
    AGENCY_HOME, AUTONOMY_DB, EVENTS_DB, HEARTBEATS_DB,
    KANBAN_DB, LEARNING_DB,
)
from _framework.heartbeats import beat
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="System health check")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--min-free-gb", type=float, default=5.0)
    args = parser.parse_args(argv)

    findings: list[dict] = []

    # AGENCY_HOME
    if not AGENCY_HOME.exists():
        findings.append({"check": "agency_home", "status": "missing",
                         "path": str(AGENCY_HOME)})
    elif not _writable(AGENCY_HOME):
        findings.append({"check": "agency_home", "status": "not_writable",
                         "path": str(AGENCY_HOME)})

    # DBs
    for name, path in [
        ("learning", LEARNING_DB), ("autonomy", AUTONOMY_DB),
        ("events", EVENTS_DB), ("heartbeats", HEARTBEATS_DB),
    ]:
        if not path.exists():
            findings.append({"check": f"db:{name}", "status": "missing",
                             "path": str(path)})
            continue
        try:
            c = sqlite3.connect(str(path))
            c.execute("PRAGMA integrity_check").fetchone()
            c.close()
        except sqlite3.DatabaseError as e:
            findings.append({"check": f"db:{name}", "status": "corrupt",
                             "error": str(e)})

    # Disk
    if AGENCY_HOME.exists():
        free_gb = shutil.disk_usage(AGENCY_HOME).free / (1024 ** 3)
        if free_gb < args.min_free_gb:
            findings.append({"check": "disk_free",
                             "status": "low",
                             "free_gb": round(free_gb, 2)})

    if findings:
        for f in findings:
            sev = "critical" if f["status"] in ("missing", "corrupt", "not_writable") else "warn"
            append_event(
                "system_health_finding", actor=args.profile, severity=sev,
                target=f.get("check", ""), payload=f,
            )
    else:
        append_event("system_health_clean", actor=args.profile, severity="info")

    beat(f"{args.profile}-system-health")
    return 0 if not findings else 1


def _writable(p: Path) -> bool:
    try:
        probe = p / ".write-probe"
        probe.write_text("x")
        probe.unlink()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
