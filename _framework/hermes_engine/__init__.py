# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Hermes engine integration — detection + installation.

HermesAgency is a Hermes-only thing: the framework layers on top of
NousResearch's Hermes engine. Without Hermes, the cron / kanban /
hermes-patches subsystems have nothing to bind to.

Public surface:

  from _framework.hermes_engine import (
      detect, is_installed, home, binary, version, HermesInfo,
      install, InstallPlan, InstallResult,
  )
"""

from __future__ import annotations

from .detection import (
    HermesInfo,
    detect, is_installed, home, binary, version,
)
from .installer import (
    InstallPlan, InstallResult,
    install, prerequisites_check,
)

__all__ = [
    "HermesInfo",
    "detect", "is_installed", "home", "binary", "version",
    "InstallPlan", "InstallResult",
    "install", "prerequisites_check",
]
