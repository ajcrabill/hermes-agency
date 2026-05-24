# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
State-vault helpers — read/write `operational-state.md` and
`conversation-journal.md`.

Hermes' learning-rule injection reduces dependency on these (rules
get into the model's context via the spine). But they remain
valuable where the rule axis doesn't fit: infrastructure status,
ongoing project status, recent operator decisions, in-progress
conversations. Pruned + maintained, they are the cross-session
memory layer.

Public API:
  read_operational_state()           full content
  read_conversation_journal()        full content
  append_to_section(file, section, body)
  init_state_vault()                 ensure files exist (called by Tier 3)
  prune(file, older_than_days)       quarter-ly maintenance
"""

from .state_files import (
    append_to_section,
    init_state_vault,
    prune,
    read_conversation_journal,
    read_operational_state,
)

__all__ = [
    "append_to_section",
    "init_state_vault",
    "prune",
    "read_conversation_journal",
    "read_operational_state",
]
