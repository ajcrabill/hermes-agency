# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Full v7 deployment migration — directory mode.

Given a v7 home directory (`~/.hermes` from the prior install, or an
extracted snapshot), this module:

  1. Runs the learning-corpus migration (delegates to v7_learning)
  2. Copies SOUL.md / standards.md to the right HermesAgency profile dirs
  3. Copies Goals.md / Values.md / Personal.md / Work.md / Client.md /
     Loriah.md / Governance.md to the profile's vault/
  4. Copies non-learning v7 DBs (book_coaching, bizdev, quality,
     hardware-watch) to `_state/v7-legacy/` for ad-hoc query while
     schema adapters are written

The expected v7 layout under `<v7_home>`:

    <v7_home>/
      .hermes/
        context/
          <profile-id>/
            Admin/
              loriah.db           ← learning corpus source
              Soul.md
              standards.md
              Goals.md / Values.md / Personal.md / Work.md / Client.md
              book_coaching.db / bizdev.db / quality.db / hardware-watch.db

(Both `.hermes/context/<profile>/Admin/` and a flatter
`<v7_home>/context/<profile>/Admin/` layout are accepted — we probe
for the first that exists.)
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from _framework.constants import (
    AGENCY_HOME, STATE_DIR,
    profile_dir, profile_soul, profile_standards,
)
from .v7_learning import (
    plan_v7_learning_migration, apply_v7_learning_migration,
    V7MigrationPlan, V7MigrationResult,
)


# Vault-shaped markdown files to copy from v7's Admin/ to the new
# profile's vault/ directory.
_VAULT_DOCS = (
    "Goals.md", "Values.md", "Personal.md", "Work.md",
    "Client.md", "Clients.md", "Loriah.md", "Governance.md",
)

# Non-learning v7 databases. Schemas may not match v0.16's framework
# tables — these land under `_state/v7-legacy/` for query, not for
# direct use by the framework. Schema-adapter work happens release-by-
# release as each subsystem matures.
_LEGACY_DBS = (
    "book_coaching.db",
    "bizdev.db",
    "quality.db",
    "hardware-watch.db",
)


@dataclass
class V7FullMigrationResult:
    """Outcome of a full directory migration."""

    profile: str
    v7_home: Path
    v7_admin_dir: Path
    learning_result: V7MigrationResult | None = None
    soul_copied: bool = False
    standards_copied: bool = False
    vault_docs_copied: list[str] = field(default_factory=list)
    legacy_dbs_copied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"v7 full migration — profile '{self.profile}':",
            f"  source: {self.v7_admin_dir}",
        ]
        if self.learning_result is not None:
            lr = self.learning_result
            lines.append(
                f"  learning corpus: {lr.applied} migrated, "
                f"{lr.failed} failed, {lr.skipped} skipped"
            )
        if self.soul_copied:
            lines.append(f"  ✓ SOUL.md")
        if self.standards_copied:
            lines.append(f"  ✓ standards.md")
        if self.vault_docs_copied:
            lines.append(f"  ✓ vault docs: {', '.join(self.vault_docs_copied)}")
        if self.legacy_dbs_copied:
            lines.append(
                f"  ✓ legacy DBs → _state/v7-legacy/: "
                f"{', '.join(self.legacy_dbs_copied)}"
            )
        if self.warnings:
            lines.append("  warnings:")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)


def discover_v7_admin_dir(v7_home: Path, profile: str = "loriah") -> Path | None:
    """Find the v7 profile's Admin/ directory under v7_home.

    Accepts either:
      <v7_home>/.hermes/context/<profile>/Admin/
      <v7_home>/context/<profile>/Admin/
      <v7_home>/Admin/  (rare: v7_home pointed directly at the profile)

    Returns the first match, or None.
    """
    candidates = [
        v7_home / ".hermes" / "context" / profile / "Admin",
        v7_home / "context" / profile / "Admin",
        v7_home / "Admin",
    ]
    for c in candidates:
        if c.is_dir() and (c / "loriah.db").exists():
            return c
    # Last-chance: any Admin/ with loriah.db underneath
    for found in v7_home.rglob("Admin/loriah.db"):
        return found.parent
    return None


def migrate_v7_full(
    v7_home: Path,
    *,
    profile: str = "loriah",
    apply: bool = True,
) -> V7FullMigrationResult:
    """Full directory migration. Returns a result whether or not
    `apply=True`; with apply=False, only the learning corpus is
    plan-only and no files are written.

    Raises FileNotFoundError if v7_home doesn't contain the expected
    layout.
    """
    v7_home = Path(v7_home).expanduser().resolve()
    admin_dir = discover_v7_admin_dir(v7_home, profile=profile)
    if admin_dir is None:
        raise FileNotFoundError(
            f"Couldn't find v7 layout under {v7_home}. Expected one of:\n"
            f"  {v7_home}/.hermes/context/{profile}/Admin/loriah.db\n"
            f"  {v7_home}/context/{profile}/Admin/loriah.db\n"
            f"  {v7_home}/Admin/loriah.db"
        )

    result = V7FullMigrationResult(
        profile=profile, v7_home=v7_home, v7_admin_dir=admin_dir,
    )

    # 1. Learning corpus
    loriah_db = admin_dir / "loriah.db"
    plan = plan_v7_learning_migration(str(loriah_db))
    if apply:
        result.learning_result = apply_v7_learning_migration(plan)
    else:
        # Plan-only mode: leave learning_result None; caller can render plan.summary()
        pass

    if not apply:
        return result

    # 2. SOUL.md
    pdir = profile_dir(profile)
    pdir.mkdir(parents=True, exist_ok=True)
    v7_soul = admin_dir / "Soul.md"
    if not v7_soul.exists():
        v7_soul = admin_dir / "SOUL.md"   # try uppercase fallback
    if v7_soul.exists():
        shutil.copy2(v7_soul, profile_soul(profile))
        result.soul_copied = True
    else:
        result.warnings.append(f"no Soul.md / SOUL.md found in {admin_dir}")

    # 3. standards.md — try a few candidate sources
    standards_src = None
    for candidate in ("standards.md", "stewardship.md"):
        if (admin_dir / candidate).exists():
            standards_src = admin_dir / candidate
            break
    if standards_src is not None:
        shutil.copy2(standards_src, profile_standards(profile))
        result.standards_copied = True
    else:
        result.warnings.append(
            f"no standards.md / stewardship.md found in {admin_dir}; "
            f"you'll need to write one"
        )

    # 4. Vault MDs
    vault_dir = pdir / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    for doc in _VAULT_DOCS:
        src = admin_dir / doc
        if src.exists():
            shutil.copy2(src, vault_dir / doc)
            result.vault_docs_copied.append(doc)

    # 5. Legacy v7 DBs → _state/v7-legacy/
    legacy_dir = STATE_DIR / "v7-legacy"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    for db in _LEGACY_DBS:
        src = admin_dir / db
        if src.exists():
            shutil.copy2(src, legacy_dir / db)
            result.legacy_dbs_copied.append(db)

    return result


__all__ = [
    "V7FullMigrationResult",
    "discover_v7_admin_dir",
    "migrate_v7_full",
]
