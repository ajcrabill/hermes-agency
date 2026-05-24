# PLUGIN — HermesAgency's integration into Hermes.
"""
HermesAgency plugin entry point.

Drop this package at `~/.hermes/plugins/hermes-agency/` (the bootstrap
installs a symlink) and Hermes discovers it on next launch. The
`register(ctx)` function wires our reliability systems into Hermes'
own lifecycle hooks:

  pre_llm_call    → inject applicable learning rules into the user
                    message of the current turn (#1 of the 7 systems)
  pre_tool_call   → autonomy gate (#2) AND send-guard (#6) check
                    for outbound mail tools
  post_tool_call  → verifier (#3) — runs the active skill's
                    verifier criteria against the tool result
  on_session_start → Sentinel observation entry (#4)
  on_session_end   → Sentinel observation exit (#4)

Kanban tracks-link (#5) and audit (#7) already operate as Hermes-
native shims/scripts — no hook needed.

Through v0.16 these were attempted via source-tree text patches in
`_framework/hermes_patches/`. v0.17 pivots to the documented Hermes
plugin API; the patches module is deprecated and removed in v0.18.

All hook handlers import lazily from `_framework/` so plugin load is
cheap; the agency state code only loads when a hook actually fires.
"""

from __future__ import annotations


def register(ctx) -> None:
    """Wire HermesAgency's reliability systems into Hermes' hooks."""
    # Hooks
    from .hooks import (
        on_pre_llm_call,
        on_pre_tool_call,
        on_post_tool_call,
        on_transform_tool_result,
        on_session_start,
        on_session_end,
    )

    ctx.register_hook("pre_llm_call",          on_pre_llm_call)
    ctx.register_hook("pre_tool_call",         on_pre_tool_call)
    ctx.register_hook("post_tool_call",        on_post_tool_call)
    ctx.register_hook("transform_tool_result", on_transform_tool_result)
    ctx.register_hook("on_session_start",      on_session_start)
    ctx.register_hook("on_session_end",        on_session_end)

    # Slash command surface — `/agency <subcommand>` inside Hermes
    from .commands import handle_agency_command
    ctx.register_command(
        "agency",
        handler=handle_agency_command,
        description="HermesAgency operations: status, next, capture, audit, setup",
    )
