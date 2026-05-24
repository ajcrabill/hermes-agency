# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Hermes patches — the integration points HermesAgency needs against
upstream Hermes that aren't exposed as stable hooks (yet).

The patches are idempotent text edits, applied via
`agency hermes-patches apply`. Each patch:

  - Locates its target file in the local Hermes install
  - Checks for an existing patch marker (idempotent)
  - Applies the change via text replacement, preserving Hermes' code
  - Records the application in `~/.agency/_health/hermes-patches.jsonl`

Re-running `apply` after a Hermes update reapplies any patches that
got reverted by the upgrade. Existing patches are detected by their
marker and skipped.

Patches shipped in v0.2:

  1. `skill_load_injection` — inserts inject_for_skill() output into
     _build_skill_message in agent/skill_commands.py. Without this,
     captured learning rules don't reach the model.

Upstream plan: file PRs proposing official hook points so the patches
become unnecessary. Until then, this is the path.
"""

from .apply import apply_all, list_patches, check_status

__all__ = ["apply_all", "list_patches", "check_status"]
