# PLUGIN — owned by HermesAgency.
"""
Setup interview subsystem — the /agency setup state machine.

Replaces the v0.1-v0.18 bash `agency init` wizard. Setup is now a
conversational flow inside Hermes:

  /agency setup                 → "migration or clean install?"
  /agency setup migrate <path>  → run migrate_v7_full, mark configured
  /agency setup clean           → start the interview
  /agency setup answer <text>   → advance one step

State persisted at ~/.hermes/agency-state/.setup-state.json between
calls (per the v0.20 parallel-state-collapse direction; falls back
to ~/.agency/.setup-state.json for pre-v0.20 deployments).

Public surface:
  handle_setup_command(rest: str) -> str
  is_configured() -> bool
  mark_configured() -> None
"""

from __future__ import annotations

from .interview import handle_setup_command, is_configured, mark_configured

__all__ = ["handle_setup_command", "is_configured", "mark_configured"]
