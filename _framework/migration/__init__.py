# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Migration tools for moving from v7 (legacy Hermes/Loriah deployment)
into HermesAgency.

v7 has accumulated valuable state — learning rules, contacts,
kanban history, dossiers, author state. Migration is operator-
controlled, traceable, and idempotent: nothing migrates unless the
operator runs an `apply` step; everything migrated is recorded in
`_health/migration-journal.jsonl` with per-source-rule traceability.

v0.7.0 scope: learning corpus only (v7's loriah.db::learning_rules
→ HermesAgency learning.db::learning_rules). Other migrations
(contacts, dossiers, author state) follow in v0.8+ as their target
subsystems mature.

Public API:

  plan_v7_learning_migration(source_db_path) → V7MigrationPlan
  apply_v7_learning_migration(plan)            → V7MigrationResult

Both are pure functions in the sense that `plan` produces a report
without writing anywhere; `apply` consumes a plan and writes to
HermesAgency's learning.db.
"""

from .v7_learning import (
    plan_v7_learning_migration,
    apply_v7_learning_migration,
    V7MigrationPlan,
    V7MigrationResult,
    V7RuleTranslation,
)
from .v7_full import (
    migrate_v7_full,
    discover_v7_admin_dir,
    V7FullMigrationResult,
)

__all__ = [
    "plan_v7_learning_migration",
    "apply_v7_learning_migration",
    "V7MigrationPlan",
    "V7MigrationResult",
    "V7RuleTranslation",
    "migrate_v7_full",
    "discover_v7_admin_dir",
    "V7FullMigrationResult",
]
