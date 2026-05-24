# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Auto-reapply Hermes patches after upgrades.

When `pip install --upgrade hermes-agent` runs, Hermes' source files
get replaced and our patches are lost. This module detects when
Hermes' install signature has changed and reapplies our patches.

How it works:

  1. After successful apply, `apply_all()` records a fingerprint
     (sha256 of the target files + Hermes version, if discoverable)
     in `~/.agency/_health/hermes-patches.lock`.
  2. `check_and_reapply()` reads the current fingerprint + compares.
     If the fingerprint differs, the targets were replaced (Hermes
     upgraded) — we reapply.
  3. The CLI subcommand `agency hermes-patches reapply` runs
     `check_and_reapply()`. Operators add it to their shell's
     post-`pip install` step (a wrapper script, a make target, etc.).
     A future v0.12+ could install an actual pip hook.

Why not a real pip hook (yet):
  - pip's post-install hooks are deprecated; entry-points-based hooks
    are limited to setup.py time.
  - A shell wrapper is operator-controllable + transparent.
  - We document the wrapper in DEPLOYMENT.md.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import HEALTH_DIR

from .apply import REGISTRY, apply_all, check_status


LOCK_PATH = HEALTH_DIR / "hermes-patches.lock"


def fingerprint_targets() -> dict[str, str]:
    """Compute a fingerprint of every patch's target file. Used to
    detect when Hermes was upgraded + our patches need re-applying."""
    fp: dict[str, str] = {}
    for p in REGISTRY:
        target = p.target_path()
        if target is None or not target.exists():
            fp[p.id] = "<no-target>"
            continue
        h = hashlib.sha256()
        try:
            h.update(target.read_bytes())
            fp[p.id] = h.hexdigest()
        except Exception:
            fp[p.id] = "<read-error>"
    return fp


def write_lock(applied_patches: list[str]) -> None:
    """Record the current fingerprint after a successful apply."""
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "applied": applied_patches,
        "fingerprint": fingerprint_targets(),
    }, indent=2), encoding="utf-8")


def read_lock() -> dict | None:
    if not LOCK_PATH.exists():
        return None
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def needs_reapply() -> tuple[bool, str]:
    """True if any target file fingerprint differs from the lock. Returns
    (needs_reapply, reason)."""
    lock = read_lock()
    if not lock:
        return True, "no prior apply recorded — apply has never run"
    saved = lock.get("fingerprint", {})
    current = fingerprint_targets()
    for patch_id, saved_fp in saved.items():
        current_fp = current.get(patch_id, "<missing>")
        if current_fp != saved_fp:
            return True, (
                f"patch {patch_id}: target fingerprint changed "
                f"({saved_fp[:12]}… → {current_fp[:12]}…)"
            )
    # Any new patches in REGISTRY since last apply?
    new_in_registry = set(p.id for p in REGISTRY) - set(saved.keys())
    if new_in_registry:
        return True, f"new patches added since last apply: {sorted(new_in_registry)}"
    return False, "fingerprints match — no reapply needed"


def check_and_reapply(dry_run: bool = False) -> dict:
    """Check fingerprints; if reapply is needed, run `apply_all()` and
    update the lock. Returns a summary dict.

    Idempotent: running on an up-to-date deployment is a no-op."""
    needs, reason = needs_reapply()
    if not needs:
        return {"reapplied": False, "reason": reason}

    if dry_run:
        return {"reapplied": False, "reason": f"would reapply: {reason}", "dry_run": True}

    statuses = apply_all()
    applied = [s.id for s in statuses if s.status == "applied"]
    write_lock(applied)
    return {
        "reapplied": True,
        "reason": reason,
        "applied_patches": applied,
        "statuses": [
            {"id": s.id, "status": s.status, "target": s.target_path}
            for s in statuses
        ],
    }


__all__ = [
    "LOCK_PATH",
    "fingerprint_targets",
    "write_lock", "read_lock",
    "needs_reapply",
    "check_and_reapply",
]
