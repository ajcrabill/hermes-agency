# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Kanban integration — HermesAgency uses Hermes' kanban_db (don't
duplicate it). This package adds the framework-specific affordances:

- The `link_type` column on `task_links` (additive schema patch,
  default 'blocks' preserves Hermes' prior behavior)
- Framework helpers (`claim_task_for_skill`, `complete_with_verifier`,
  `add_link`)
- A resolver for the active kanban DB path (matches Hermes' lookup
  order so `_framework.constants.KANBAN_DB` always points to the
  same DB the operator's `hermes kanban` CLI sees)
"""

from .integration import (
    active_kanban_db,
    apply_schema_patch,
    schema_patch_applied,
)
from .helpers import (
    add_link,
    blocking_parents,
    children,
    claim_task_for_skill,
    complete_with_verifier,
)

__all__ = [
    "active_kanban_db",
    "apply_schema_patch",
    "schema_patch_applied",
    "add_link",
    "blocking_parents",
    "children",
    "claim_task_for_skill",
    "complete_with_verifier",
]
