# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Base class + helpers for Hermes patches.

Every patch:
  - has a stable `id` (lives in the marker comment + the journal)
  - implements `applies_to(file_text) -> bool` — should we patch
  - implements `is_already_applied(file_text) -> bool` — marker check
  - implements `apply(file_text) -> str` — returns the patched text
  - implements `target_path() -> Path | None` — where to write

The orchestrator (`apply.py`) handles backup, idempotency, and
journaling.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path


def hermes_install_root() -> Path:
    """Resolve the local Hermes install root.

    Prefer the `hermes-agent` directory inside `$HERMES_HOME`; fall
    back to `~/.hermes/hermes-agent` (Hermes' default install layout).
    """
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    candidate = hermes_home / "hermes-agent"
    return candidate


class HermesPatch(ABC):
    """One patch against Hermes."""

    id: str = ""           # stable identifier; shows in the marker
    description: str = ""

    @abstractmethod
    def target_path(self) -> Path | None:
        """Return the file this patch targets, or None if missing."""

    @abstractmethod
    def applies_to(self, file_text: str) -> bool:
        """True if the patch is appropriate to apply against this text
        (e.g. the anchor for the insertion is present)."""

    @abstractmethod
    def apply(self, file_text: str) -> str:
        """Return the patched text. Must be idempotent if the marker is
        present (caller will check first via is_already_applied)."""

    @abstractmethod
    def is_already_applied(self, file_text: str) -> bool:
        """Marker check — True if our prior patch is already there."""

    @property
    def marker(self) -> str:
        return f"# HERMES_AGENCY_PATCH:{self.id}"


__all__ = ["HermesPatch", "hermes_install_root"]
