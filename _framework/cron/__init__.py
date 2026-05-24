# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Hermes-cron integration.

HermesAgency does NOT run its own scheduler. Hermes handles runtime;
we register jobs into Hermes' `jobs.json` registry and let Hermes
fire them.

Per-profile authoring: each profile maintains `profiles/<id>/cron/jobs.json`
in the same shape Hermes expects (id, name, prompt, schedule,
provider, etc.). `agency cron sync` merges all per-profile jobs
into Hermes' canonical `~/.hermes/cron/jobs.json`.

Jobs owned by HermesAgency are tagged with `origin: "hermes-agency"`
so subsequent syncs replace them cleanly without disturbing operator-
authored jobs.
"""

from .sync import sync_cron_jobs, list_jobs

__all__ = ["sync_cron_jobs", "list_jobs"]
