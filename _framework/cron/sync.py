# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Sync per-profile cron/jobs.json into Hermes' canonical jobs registry.

Hermes' format (~/.hermes/cron/jobs.json):

  {
    "jobs": [
      {
        "id": "<12-hex>",
        "name": "<display name>",
        "prompt": "<the prompt the agent runs>",
        "skills": [],
        "skill": "<skill name or null>",
        "model": "<model id>",
        "provider": "<provider id>",
        "base_url": "<endpoint>",
        "schedule": { "kind": "interval", "minutes": 5 },
        "enabled": true,
        ...
      }
    ]
  }

HermesAgency-owned jobs carry `origin: "hermes-agency"` + a stable
`hermes_agency_key: "<profile>:<job-name>"` so subsequent syncs
replace them in-place.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _framework.constants import PROFILES_DIR


def hermes_jobs_json() -> Path:
    """Path to Hermes' canonical jobs.json."""
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    return hermes_home / "cron" / "jobs.json"


def list_jobs(profile: str | None = None) -> list[dict]:
    """List jobs HermesAgency would register (from per-profile jobs.json files)."""
    out: list[dict] = []
    if not PROFILES_DIR.exists():
        return out
    profiles = [PROFILES_DIR / profile] if profile else sorted(PROFILES_DIR.iterdir())
    for prof_dir in profiles:
        if not prof_dir.is_dir():
            continue
        jobs_file = prof_dir / "cron" / "jobs.json"
        if not jobs_file.exists():
            continue
        try:
            with open(jobs_file) as f:
                doc = json.load(f)
        except Exception:
            continue
        for job in doc.get("jobs", []):
            job = dict(job)
            job["_profile"] = prof_dir.name
            out.append(job)
    return out


def sync_cron_jobs(dry_run: bool = False) -> dict[str, Any]:
    """Merge per-profile jobs into Hermes' jobs.json.

    Strategy:
      - Read Hermes' jobs.json (or initialize an empty one)
      - Drop every existing job with `origin: "hermes-agency"`
      - Add fresh entries from each profile's cron/jobs.json
      - Tag added entries with origin + hermes_agency_key + canonical id

    Operator-authored jobs (origin != "hermes-agency") are preserved
    untouched.

    Returns a summary dict.
    """
    target = hermes_jobs_json()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        try:
            with open(target) as f:
                existing = json.load(f)
        except Exception:
            existing = {"jobs": []}
    else:
        existing = {"jobs": []}

    operator_jobs = [j for j in existing.get("jobs", []) if j.get("origin") != "hermes-agency"]
    framework_jobs_before = [j for j in existing.get("jobs", []) if j.get("origin") == "hermes-agency"]

    new_framework_jobs: list[dict] = []
    for job in list_jobs():
        profile = job.pop("_profile")
        canonical_key = f"{profile}:{job.get('name', 'unnamed')}"
        canonical_id = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:12]

        # Preserve operator-tracked counters when present (last_run_at, repeat.completed, etc.)
        prior = next((p for p in framework_jobs_before if p.get("hermes_agency_key") == canonical_key), None)

        merged = {
            **job,
            "id": canonical_id,
            "hermes_agency_key": canonical_key,
            "origin": "hermes-agency",
            "profile": profile,
        }
        if prior:
            # Carry forward state fields so Hermes doesn't reset cadence
            for k in ("last_run_at", "last_status", "last_error", "next_run_at"):
                if k in prior and k not in merged:
                    merged[k] = prior[k]
            if "repeat" in prior and "repeat" not in merged:
                merged["repeat"] = prior["repeat"]
        new_framework_jobs.append(merged)

    merged_doc = {
        **existing,
        "jobs": operator_jobs + new_framework_jobs,
        "hermes_agency_synced_at": datetime.now(timezone.utc).isoformat(),
    }

    if not dry_run:
        with open(target, "w") as f:
            json.dump(merged_doc, f, indent=2)

    return {
        "target": str(target),
        "operator_jobs": len(operator_jobs),
        "framework_jobs_before": len(framework_jobs_before),
        "framework_jobs_after": len(new_framework_jobs),
        "dry_run": dry_run,
    }


__all__ = ["sync_cron_jobs", "list_jobs", "hermes_jobs_json"]
