# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Hermes engine detection.

HermesAgency layers on top of NousResearch's Hermes engine. Without
Hermes present, the framework has nothing to bridge to — no scheduler
for cron sync, no kanban for the integration shim, no skill runner.

This module is the single source of truth for "is Hermes here?" and
"if so, where?". Every other subsystem that touches Hermes (cron sync,
hermes-patches, kanban integration) reads from here.

Detection signals, in priority order:

  1. $HERMES_HOME env var, if it points at a valid Hermes data dir
  2. ~/.hermes/ if it has the expected structure
  3. `hermes` binary on PATH, with its --version response

A "valid Hermes home" has, at minimum:
  - A `hermes-agent/` subdir (the source tree), OR
  - A `state.db` file (the engine state), OR
  - A `kanban.db` file (the kanban store)

We're lenient: if any of those exist, we assume Hermes lives here.
Strict validation happens in the installer's verify_install() step.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


# Subdirs / files that signal "this is a Hermes data dir"
_HERMES_HOME_MARKERS = (
    "hermes-agent",     # source tree
    "state.db",         # engine state
    "kanban.db",        # kanban store
    "scheduler.db",     # cron scheduler
)


@dataclass
class HermesInfo:
    """What we know about the local Hermes install (if any)."""

    installed: bool
    home: Path | None = None             # HERMES_HOME equivalent
    binary: Path | None = None           # path to `hermes` executable
    version: str | None = None           # output of `hermes --version`
    source_dir: Path | None = None       # hermes-agent/ source tree
    detected_via: str = ""               # "env", "default-home", "path", or ""


def detect() -> HermesInfo:
    """Locate Hermes on this system. Returns HermesInfo with installed=False
    if nothing is found.

    Order: env > default home (~/.hermes) > PATH lookup. We don't combine
    signals — first hit wins, and we report which one fired so the wizard
    can show the user.
    """
    # 1. $HERMES_HOME
    env_home = os.environ.get("HERMES_HOME", "").strip()
    if env_home:
        home = Path(env_home).expanduser()
        if _looks_like_hermes_home(home):
            return _build_info(home, detected_via="env")

    # 2. ~/.hermes default
    default_home = Path.home() / ".hermes"
    if _looks_like_hermes_home(default_home):
        return _build_info(default_home, detected_via="default-home")

    # 3. `hermes` on PATH (even if HERMES_HOME isn't set)
    binary = shutil.which("hermes")
    if binary:
        bpath = Path(binary).resolve()
        # Derive a likely home: if binary is at <home>/hermes-agent/venv/bin/hermes,
        # walk back up. Otherwise fall back to ~/.hermes.
        likely_home = _home_from_binary(bpath) or default_home
        if _looks_like_hermes_home(likely_home):
            return _build_info(
                likely_home, binary=bpath, detected_via="path",
            )
        # Binary exists but no recognizable home — record what we know
        return HermesInfo(
            installed=True, binary=bpath, version=_version_of(bpath),
            detected_via="path-binary-only",
        )

    return HermesInfo(installed=False)


def is_installed() -> bool:
    """Convenience: True iff Hermes is detectable on this system."""
    return detect().installed


def home() -> Path | None:
    """Convenience: the resolved HERMES_HOME, or None if not detected."""
    return detect().home


def binary() -> Path | None:
    """Convenience: the resolved `hermes` binary path, or None if not detected."""
    return detect().binary


def version() -> str | None:
    """Convenience: Hermes version string, or None if not detected."""
    return detect().version


# ── Internals ─────────────────────────────────────────────────────────────


def _looks_like_hermes_home(p: Path) -> bool:
    """Lenient check: any of the marker files / dirs present?"""
    if not p.exists() or not p.is_dir():
        return False
    return any((p / marker).exists() for marker in _HERMES_HOME_MARKERS)


def _build_info(home: Path, *,
                binary: Path | None = None,
                detected_via: str) -> HermesInfo:
    """Fill out a HermesInfo from a resolved home dir."""
    source = home / "hermes-agent"
    if not source.exists():
        source = None

    # Find the binary if not provided
    if binary is None:
        # Common layout: <home>/hermes-agent/venv/bin/hermes
        candidate = home / "hermes-agent" / "venv" / "bin" / "hermes"
        if candidate.exists():
            binary = candidate
        else:
            path_binary = shutil.which("hermes")
            if path_binary:
                binary = Path(path_binary).resolve()

    return HermesInfo(
        installed=True,
        home=home,
        binary=binary,
        version=_version_of(binary) if binary else None,
        source_dir=source,
        detected_via=detected_via,
    )


def _version_of(binary: Path | None) -> str | None:
    """Run `<binary> --version` and parse the version string."""
    if not binary or not binary.exists():
        return None
    try:
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    # Typical: "Hermes Agent v0.14.0 (2026.5.16)"
    line = (result.stdout + result.stderr).strip().splitlines()
    return line[0] if line else None


def _home_from_binary(binary: Path) -> Path | None:
    """If binary is at <X>/hermes-agent/venv/bin/hermes, return <X>."""
    parts = binary.parts
    # Walk backward looking for 'hermes-agent'
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "hermes-agent":
            return Path(*parts[:i]) if i > 0 else None
    return None


__all__ = [
    "HermesInfo",
    "detect", "is_installed", "home", "binary", "version",
]
