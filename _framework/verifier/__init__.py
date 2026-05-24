# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Verifier — typed completion, fail-closed.

Every kanban-completing skill declares a `## Verifier criteria`
section. Each criterion has:

  - type:     one of the 10 registered criterion types
  - args:     type-specific parameters

`verifier.check(task_id)` looks up the task's criteria, executes each,
and returns 0 if every criterion passes; 1 otherwise. Zero criteria
also means 1 (fail-closed; the framework refuses completion of
unverifiable work).

Registered criterion types (v0.1):

  file_exists           args: { path: str }
  file_contains         args: { path: str, needle: str }
  file_not_contains     args: { path: str, needle: str }
  sql_query             args: { db: str, query: str, expect_rows: int }
  kanban_status         args: { task_id: str, status: str }
  kanban_descendants_done args: { task_id: str }
  learning_rule_recorded args: { source_contains: str }   # capture happened
  firing_recorded        args: { rule_id: str, skill_tag: str }
  http_status            args: { url: str, expect: int }
  shell_exit_zero        args: { command: str }            # used sparingly

Types live in `_framework/verifier/criterion_types/<type>.py`. Adding
a type is a one-file PR + a one-line entry in this module's REGISTRY.
"""

from .verifier import (
    Verifier,
    VerificationResult,
    CriterionFailure,
    check,
    list_types,
)

__all__ = ["Verifier", "VerificationResult", "CriterionFailure", "check", "list_types"]
