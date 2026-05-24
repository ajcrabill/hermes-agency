# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
v0.20 state-collapse migration.

Through v0.19, agency state lived at:
  ~/.agency/_state/    — databases (learning, autonomy, events, etc.)
  ~/.agency/_health/   — audit reports, operator actions log

v0.20 collapses both to:
  ~/.hermes/agency-state/         — databases
  ~/.hermes/agency-state/_health/ — audit reports + ops log

This module moves a pre-v0.20 deployment to the v0.20+ layout.
Idempotent: re-runs are no-ops. Reversible: state files are MOVED
(not copied), but the legacy paths get a tombstone marker so audit
can detect a pre-v0.20 deployment that needs migrating.

Public entry:
    plan_state_collapse() -> StateCollapsePlan
    apply_state_collapse(plan) -> StateCollapseResult
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class StateCollapsePlan:
    """Pre-apply summary."""

    legacy_state_dir: Path
    legacy_health_dir: Path
    target_state_dir: Path
    target_health_dir: Path
    files_to_move: list[Path] = field(default_factory=list)
    already_migrated: bool = False
    nothing_to_migrate: bool = False
    issues: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.already_migrated:
            return (f"State already at v0.20+ location ({self.target_state_dir}).\n"
                    f"  Nothing to do.")
        if self.nothing_to_migrate:
            return (f"No state files found at legacy location ({self.legacy_state_dir}).\n"
                    f"  Looks like a fresh install — nothing to migrate.")
        lines = [
            f"State collapse plan:",
            f"  from: {self.legacy_state_dir}",
            f"        {self.legacy_health_dir}",
            f"  to:   {self.target_state_dir}",
            f"        {self.target_health_dir}",
            f"  files: {len(self.files_to_move)} to move",
        ]
        for f in self.files_to_move[:10]:
            lines.append(f"    · {f.name}")
        if len(self.files_to_move) > 10:
            lines.append(f"    · ... + {len(self.files_to_move) - 10} more")
        if self.issues:
            lines.append("  issues:")
            for i in self.issues:
                lines.append(f"    ⚠ {i}")
        return "\n".join(lines)


@dataclass
class StateCollapseResult:
    """Outcome of apply_state_collapse()."""

    success: bool
    moved: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    target_state_dir: Optional[Path] = None
    target_health_dir: Optional[Path] = None
    tombstone_written: bool = False
    applied_at: str = ""

    def summary(self) -> str:
        lines = [
            f"State collapse {'✓ complete' if self.success else '✗ FAILED'}.",
            f"  moved: {len(self.moved)} files",
            f"  failed: {len(self.failed)}",
        ]
        if self.target_state_dir:
            lines.append(f"  state now at: {self.target_state_dir}")
        if self.failed:
            lines.append("  failures:")
            for path, reason in self.failed[:5]:
                lines.append(f"    ✗ {path.name}: {reason}")
        return "\n".join(lines)


def _legacy_paths() -> tuple[Path, Path]:
    """Return (legacy_state_dir, legacy_health_dir) — both under
    `$AGENCY_HOME` regardless of current STATE_DIR resolution."""
    import os
    agency_home = Path(
        os.environ.get("AGENCY_HOME", Path.home() / ".agency")
    ).expanduser()
    return agency_home / "_state", agency_home / "_health"


def _target_paths() -> tuple[Path, Path]:
    """Return (target_state_dir, target_health_dir) — the v0.20+ location
    under $HERMES_HOME (or ~/.hermes)."""
    import os
    hermes_home = Path(
        os.environ.get("HERMES_HOME", Path.home() / ".hermes")
    ).expanduser()
    target_state = hermes_home / "agency-state"
    target_health = target_state / "_health"
    return target_state, target_health


def plan_state_collapse() -> StateCollapsePlan:
    """Inspect filesystem; return a plan describing what would be moved."""
    legacy_state, legacy_health = _legacy_paths()
    target_state, target_health = _target_paths()

    plan = StateCollapsePlan(
        legacy_state_dir=legacy_state,
        legacy_health_dir=legacy_health,
        target_state_dir=target_state,
        target_health_dir=target_health,
    )

    # Already at v0.20+ location?
    if target_state.exists() and any(target_state.iterdir()):
        if not legacy_state.exists() or not any(legacy_state.iterdir()):
            plan.already_migrated = True
            return plan

    # Nothing to migrate?
    if not legacy_state.exists() and not legacy_health.exists():
        plan.nothing_to_migrate = True
        return plan

    # Collect files to move
    files: list[Path] = []
    if legacy_state.exists():
        for p in sorted(legacy_state.rglob("*")):
            if p.is_file():
                files.append(p)
    if legacy_health.exists():
        for p in sorted(legacy_health.rglob("*")):
            if p.is_file():
                files.append(p)
    plan.files_to_move = files

    # Sanity checks
    if target_state.exists() and any(target_state.iterdir()):
        plan.issues.append(
            f"Target {target_state} already has content. "
            "The migration will MERGE, preferring legacy files on collision."
        )

    return plan


def apply_state_collapse(plan: StateCollapsePlan) -> StateCollapseResult:
    """Perform the move. Files are atomically moved (shutil.move) one
    by one. On failure mid-way, the partially-moved state is left
    in place — re-running plan + apply picks up where it stopped."""
    result = StateCollapseResult(
        success=False,
        target_state_dir=plan.target_state_dir,
        target_health_dir=plan.target_health_dir,
        applied_at=datetime.now(timezone.utc).isoformat(),
    )

    if plan.already_migrated or plan.nothing_to_migrate:
        result.success = True
        return result

    # Create target dirs
    plan.target_state_dir.mkdir(parents=True, exist_ok=True)
    plan.target_health_dir.mkdir(parents=True, exist_ok=True)

    for src in plan.files_to_move:
        # Compute destination path: preserve subpath under legacy root
        if plan.legacy_state_dir in src.parents or src == plan.legacy_state_dir:
            rel = src.relative_to(plan.legacy_state_dir)
            dst = plan.target_state_dir / rel
        elif plan.legacy_health_dir in src.parents or src == plan.legacy_health_dir:
            rel = src.relative_to(plan.legacy_health_dir)
            dst = plan.target_health_dir / rel
        else:
            result.failed.append((src, "file not under expected legacy root"))
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dst.exists():
                # Collision: prefer legacy (operator's existing data)
                dst.unlink()
            shutil.move(str(src), str(dst))
            result.moved.append(dst)
        except Exception as e:
            result.failed.append((src, str(e)))

    # Write a tombstone marker at the legacy location so future audits
    # know this deployment has been migrated. Don't delete the empty
    # legacy dirs — they're harmless markers and aid debugging.
    try:
        tombstone = plan.legacy_state_dir.parent / "_state.MIGRATED-TO-v0.20"
        tombstone.write_text(
            f"State collapsed to {plan.target_state_dir} on {result.applied_at}\n"
            f"Files moved: {len(result.moved)}\n"
            f"Run `agency state-location` to see the current state root.\n",
            encoding="utf-8",
        )
        result.tombstone_written = True
    except OSError:
        pass

    result.success = (len(result.failed) == 0)
    return result


__all__ = [
    "StateCollapsePlan", "StateCollapseResult",
    "plan_state_collapse", "apply_state_collapse",
]
