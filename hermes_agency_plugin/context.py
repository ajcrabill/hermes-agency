# PLUGIN — owned by HermesAgency.
"""
Context resolution for plugin hooks.

Hermes' lifecycle hooks don't pass `profile` / `role` directly — that
information lives in HermesAgency's deployment.yaml. This module
resolves "which profile is the agency wired to" so the hooks can
load the right learning rules / autonomy state / verifier criteria.

For v0.17 the resolution is simple: use the default profile from
deployment.yaml (the CoS). v0.18+ adds per-session profile awareness
once we can route different Hermes conversations to different
agency profiles.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional


@functools.lru_cache(maxsize=1)
def _agency_home() -> Path:
    """Resolve ~/.agency. Cached for the process lifetime — agency
    home doesn't move between hook invocations."""
    import os
    return Path(os.environ.get("AGENCY_HOME", str(Path.home() / ".agency")))


def current_profile_and_role() -> tuple[Optional[str], Optional[str]]:
    """Return (profile_id, role) for the deployment's primary profile.

    Returns (None, None) if no deployment exists yet, deployment.yaml
    is malformed, or no chief-of-staff profile is declared.
    """
    deployment_yaml = _agency_home() / "deployment.yaml"
    if not deployment_yaml.exists():
        return None, None
    try:
        import yaml
        doc = yaml.safe_load(deployment_yaml.read_text(encoding="utf-8")) or {}
    except Exception:
        return None, None

    profiles = doc.get("profiles", []) or []
    # Prefer chief-of-staff if present
    for p in profiles:
        if isinstance(p, dict) and p.get("role") == "chief-of-staff":
            return p.get("id"), p.get("role")
    # Otherwise first profile
    if profiles and isinstance(profiles[0], dict):
        return profiles[0].get("id"), profiles[0].get("role")
    return None, None


def is_configured() -> bool:
    """True if the deployment has been through setup (clean-install
    interview or v7 migration). Determined by the presence of the
    `~/.agency/.configured` marker.

    Returns False on a fresh install where setup hasn't run.
    """
    return (_agency_home() / ".configured").exists()


__all__ = [
    "current_profile_and_role",
    "is_configured",
]
