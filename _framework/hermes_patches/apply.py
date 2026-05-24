# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Orchestrates Hermes patches: discovery, idempotency, backup, journal.

Public entry:
  apply_all()       run every registered patch
  check_status()    report each patch's status without applying
  list_patches()    enumerate registered patches
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import HEALTH_DIR

# v0.17 NOTE: REGISTRY is intentionally empty. Through v0.16, this list
# carried `SkillLoadInjectionPatch()` — a text-anchor patch into Hermes'
# `agent/skill_commands.py::_build_skill_message`. v0.17 pivoted to the
# documented Hermes plugin API (`hermes_agency_plugin/`); the learning-
# rule injection now happens via the plugin's `pre_llm_call` hook instead
# of mutating Hermes' source.
#
# The `skill_load_injection.py` module is kept temporarily for back-
# compat with v0.16 deployments that have already applied the patch
# (operators can `agency hermes-patches apply` to no-op cleanly during
# the transition). It will be deleted in v0.18.
REGISTRY: list = []


# The 7 reliability systems HermesAgency is meant to add to Hermes.
# Each entry says: what's the system, which patch wires it in, and
# whether that patch exists yet.
#
# This list is the honest source of truth for "how much of HermesAgency
# is actually Hermes-extending vs. parallel infrastructure." Display
# this via `agency hermes-patches status --systems`.
# As of v0.17, all 7 systems are wired into Hermes via the documented
# Hermes plugin API (`hermes_agency_plugin/` at the repo root, symlinked
# into `~/.hermes/plugins/hermes-agency/` by bootstrap.sh). The text-
# anchor patches from v0.2-v0.16 are deprecated and no longer registered
# in REGISTRY.
SYSTEM_INVENTORY: list[dict] = [
    {
        "id": "learning-loop",
        "name": "Supervised learning loop",
        "patch_id": "plugin:pre_llm_call hook",
        "patch_exists": True,
        "note": "Plugin's pre_llm_call hook injects applicable rules into "
                "the user message of each turn. Replaces v0.2-v0.16's "
                "skill-load-injection text patch.",
    },
    {
        "id": "autonomy-ladder",
        "name": "Autonomy ladder (L1–L5)",
        "patch_id": "plugin:pre_tool_call hook",
        "patch_exists": True,
        "note": "Plugin's pre_tool_call hook consults the autonomy ladder; "
                "returns a block message if the skill lacks authority for "
                "the tool's action class. New in v0.17.",
    },
    {
        "id": "verifier",
        "name": "Verifier (per-skill criteria)",
        "patch_id": "plugin:post_tool_call hook",
        "patch_exists": True,
        "note": "Plugin's post_tool_call hook records tool completion to "
                "events.db (v0.17 = observation). v0.18 adds enforcement "
                "via transform_tool_result that rewrites failed-verifier "
                "outputs into actionable errors.",
    },
    {
        "id": "sentinel",
        "name": "System Sentinel (read-only observer)",
        "patch_id": "plugin:on_session_start/end hooks",
        "patch_exists": True,
        "note": "Plugin's session hooks record session_started/ended events "
                "to events.db. Sentinel reads from there + Hermes' own "
                "state.db. Read-only, no mutations.",
    },
    {
        "id": "kanban-tracks",
        "name": "Kanban tracks-link type",
        "patch_id": "(shim — agency writes tracks rows to Hermes' kanban.db)",
        "patch_exists": True,
        "note": "Already shaped correctly: kanban shim writes to Hermes' "
                "own kanban.db with the 'tracks' link type. Hermes-native.",
    },
    {
        "id": "send-guard",
        "name": "Send-guard (outbound mail gate)",
        "patch_id": "plugin:pre_tool_call hook (mail tools)",
        "patch_exists": True,
        "note": "Plugin's pre_tool_call hook filters for outbound-mail "
                "tools and runs send_guard.evaluate before allowing. "
                "Blocks on hard-rule violations or access-list deny. "
                "New in v0.17.",
    },
    {
        "id": "audit",
        "name": "Audit (weekly alignment check)",
        "patch_id": "(script — audit runs over Hermes state on schedule)",
        "patch_exists": True,
        "note": "Already shaped correctly: audit-alignment runs as a "
                "scheduled script reading Hermes state + agency state. "
                "Cron-fired.",
    },
]


JOURNAL_PATH = HEALTH_DIR / "hermes-patches.jsonl"


@dataclass
class PatchStatus:
    id: str
    target_path: str | None       # absolute path or None if missing
    status: str                    # 'applied' | 'unapplied' | 'target-missing' | 'anchor-missing'
    description: str = ""
    last_applied_at: str | None = None


def list_patches() -> list:
    """Enumerate the registered patches (objects)."""
    return list(REGISTRY)


def check_status() -> list[PatchStatus]:
    """For each patch: where is it? Is it applied? Returns a list."""
    out: list[PatchStatus] = []
    for p in REGISTRY:
        target = p.target_path()
        if target is None:
            out.append(PatchStatus(id=p.id, target_path=None, status="target-missing",
                                    description=p.description))
            continue
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception:
            out.append(PatchStatus(id=p.id, target_path=str(target), status="target-missing",
                                    description=p.description))
            continue
        if p.is_already_applied(text):
            out.append(PatchStatus(id=p.id, target_path=str(target), status="applied",
                                    description=p.description))
        elif p.applies_to(text):
            out.append(PatchStatus(id=p.id, target_path=str(target), status="unapplied",
                                    description=p.description))
        else:
            out.append(PatchStatus(id=p.id, target_path=str(target), status="anchor-missing",
                                    description=p.description))
    return out


def apply_all(dry_run: bool = False) -> list[PatchStatus]:
    """Apply every patch. Idempotent. Returns post-state status."""
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)

    for p in REGISTRY:
        target = p.target_path()
        if target is None:
            continue
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if p.is_already_applied(text):
            continue
        if not p.applies_to(text):
            _journal(p.id, target, status="anchor-missing",
                      note="anchor not found; Hermes file may have changed")
            continue
        patched = p.apply(text)
        if dry_run:
            continue
        # Back up the original alongside (one backup per patch invocation)
        backup_dir = target.parent / "_hermes_agency_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{target.name}.{_ts()}.bak"
        shutil.copy2(target, backup_path)
        target.write_text(patched, encoding="utf-8")
        _journal(p.id, target, status="applied", backup=str(backup_path))

    return check_status()


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def _journal(patch_id: str, target: Path, status: str, **extra) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "patch": patch_id,
        "target": str(target),
        "status": status,
        **extra,
    }
    try:
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def system_inventory() -> list[dict]:
    """Return the 7-system inventory with current applied/unapplied
    status overlaid for systems that have a patch built."""
    statuses_by_patch_id = {s.id: s for s in check_status()}
    out: list[dict] = []
    for system in SYSTEM_INVENTORY:
        entry = dict(system)  # copy
        if entry["patch_exists"] and entry["patch_id"] in statuses_by_patch_id:
            ps = statuses_by_patch_id[entry["patch_id"]]
            entry["applied_status"] = ps.status      # applied / unapplied / target-missing / anchor-missing
        elif entry["patch_exists"]:
            entry["applied_status"] = "n/a"          # built-in (sentinel, kanban, audit) — no patch to apply
        else:
            entry["applied_status"] = "not-built"    # the gap — TODO patches
        out.append(entry)
    return out


__all__ = [
    "apply_all", "check_status", "list_patches",
    "PatchStatus", "REGISTRY",
    "SYSTEM_INVENTORY", "system_inventory",
]
