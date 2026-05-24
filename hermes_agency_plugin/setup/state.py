# PLUGIN — owned by HermesAgency.
"""
Setup state machine — persisted between /agency setup calls.

The state machine is a simple JSON blob with `kind` (migration vs.
clean), `current_step` (string), and `collected_answers` (dict of
field-name → answer). Each /agency setup call loads the state,
advances if appropriate, and re-saves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from hermes_agency_plugin.context import _agency_home


# Where state lives. Try ~/.hermes/agency-state/ first (the v0.20+
# target), fall back to ~/.agency/_state/ for pre-v0.20 deployments.
def _state_path() -> Path:
    new_home = Path.home() / ".hermes" / "agency-state"
    if new_home.exists():
        return new_home / ".setup-state.json"
    # Pre-v0.20 fallback
    return _agency_home() / ".setup-state.json"


def _configured_marker_path() -> Path:
    new_home = Path.home() / ".hermes" / "agency-state"
    if new_home.exists():
        return new_home / ".configured"
    return _agency_home() / ".configured"


@dataclass
class SetupState:
    """Persisted interview state."""

    kind: str = ""                      # "" | "migration" | "clean"
    current_step: str = "INITIAL"       # current state-machine node
    collected_answers: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "current_step": self.current_step,
            "collected_answers": self.collected_answers,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SetupState":
        return cls(
            kind=d.get("kind", ""),
            current_step=d.get("current_step", "INITIAL"),
            collected_answers=d.get("collected_answers", {}),
        )


def load_state() -> SetupState:
    """Load the persisted state, or return a fresh INITIAL state."""
    path = _state_path()
    if not path.exists():
        return SetupState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return SetupState()
    return SetupState.from_dict(data)


def save_state(state: SetupState) -> None:
    """Persist the state to disk. Creates parent dirs if needed."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def clear_state() -> None:
    """Remove the persisted state (called after setup completes)."""
    path = _state_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def is_configured() -> bool:
    """True iff the .configured marker exists."""
    return _configured_marker_path().exists()


def mark_configured() -> None:
    """Write the .configured marker."""
    p = _configured_marker_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()


__all__ = [
    "SetupState",
    "load_state", "save_state", "clear_state",
    "is_configured", "mark_configured",
]
