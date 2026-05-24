#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
hardware-watch — basic hardware vitals (CPU load, RAM, disk).

For deployments running on a local machine (the small-agency default).
Multi-machine deployments will replace this with a remote-collection
script. Emits events; files kanban alerts on thresholds.
"""

from __future__ import annotations

import argparse
import sys

from _framework.heartbeats import beat
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hardware watch")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--cpu-warn-pct", type=float, default=80.0)
    parser.add_argument("--mem-warn-pct", type=float, default=85.0)
    args = parser.parse_args(argv)

    metrics: dict = {}
    try:
        import psutil   # type: ignore[import-not-found]
    except ImportError:
        # Fall back to OS commands (macOS / linux)
        metrics = _fallback_metrics()
    else:
        metrics = {
            "cpu_pct": psutil.cpu_percent(interval=1),
            "mem_pct": psutil.virtual_memory().percent,
            "disk_pct": psutil.disk_usage("/").percent,
        }

    findings = []
    if metrics.get("cpu_pct", 0) > args.cpu_warn_pct:
        findings.append({"metric": "cpu_pct", "value": metrics["cpu_pct"],
                         "threshold": args.cpu_warn_pct})
    if metrics.get("mem_pct", 0) > args.mem_warn_pct:
        findings.append({"metric": "mem_pct", "value": metrics["mem_pct"],
                         "threshold": args.mem_warn_pct})

    severity = "warn" if findings else "info"
    append_event(
        "hardware_watch_ran", actor=args.profile, severity=severity,
        payload={"metrics": metrics, "findings": findings},
    )
    beat(f"{args.profile}-hardware-watch")
    return 0


def _fallback_metrics() -> dict:
    """Minimal cross-platform fallback when psutil isn't installed."""
    import os
    import shutil

    try:
        load1, _, _ = os.getloadavg()
    except OSError:
        load1 = 0.0
    try:
        usage = shutil.disk_usage("/")
        disk_pct = usage.used / usage.total * 100
    except Exception:
        disk_pct = 0.0
    return {"load_avg_1m": load1, "disk_pct": round(disk_pct, 1)}


if __name__ == "__main__":
    sys.exit(main())
