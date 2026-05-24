# PLUGIN — owned by HermesAgency.
"""
The 7-reliability-system integration inventory.

This is the public honesty surface for "which reliability systems
HermesAgency claims, and which are actually Hermes-extending today."
Exposed via `agency hermes-patches systems` (shell) and `/agency
systems` (Hermes slash command).

Moved here from `_framework/hermes_patches/apply.py` in v0.18 as
part of deleting the deprecated text-anchor patch module.
"""

from __future__ import annotations


# As of v0.17, all 7 systems are wired into Hermes via the documented
# Hermes plugin API (`hermes_agency_plugin/`). The text-anchor patches
# from v0.2-v0.16 are deprecated and removed in v0.18.
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
        "patch_id": "plugin:transform_tool_result hook",
        "patch_exists": True,
        "note": "Plugin's transform_tool_result hook (v0.18+) runs verifier "
                "criteria against tool outputs. For write/patch tools it "
                "constructs ad-hoc file_exists / file_contains criteria. "
                "Failures get rewritten as actionable LLM errors. v0.21 "
                "adds per-skill criteria from frontmatter once Hermes' "
                "agentskills.io context is available.",
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


def system_inventory() -> list[dict]:
    """Return the 7-system inventory with an `applied_status` field
    overlaid. As of v0.17, all 7 systems are wired via the plugin API,
    so every entry reports applied_status='applied'."""
    out: list[dict] = []
    for system in SYSTEM_INVENTORY:
        entry = dict(system)
        entry["applied_status"] = "applied" if entry["patch_exists"] else "not-built"
        out.append(entry)
    return out


__all__ = ["SYSTEM_INVENTORY", "system_inventory"]
