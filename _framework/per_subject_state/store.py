# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Per-subject state store — filesystem layout + I/O.

Directory:
  <profile vault>/<subject_type>/<subject_id>/
    state.json       metadata + momentum
    voice.md         (optional) voice profile, used by writing-support
    profile.md       longer-form context about the subject
    history.md       interaction log, append-only

Namespace guard: every operation validates that subject_id is
filesystem-safe (no `..`, no `/`, no leading dot). Cross-subject
contamination — author A's state landing in author B's dir — is
the failure mode this prevents.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import profile_vault


_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")


def _validate_id(subject_id: str) -> str:
    """Refuse paths that would escape the subject namespace."""
    if not subject_id or not _SAFE_ID_RE.match(subject_id):
        raise ValueError(
            f"subject_id must match {_SAFE_ID_RE.pattern}, got {subject_id!r}"
        )
    return subject_id


def subject_root(profile: str, subject_type: str, subject_id: str) -> Path:
    """Return the absolute directory for a (profile, subject_type, subject_id)."""
    _validate_id(subject_type)
    _validate_id(subject_id)
    return profile_vault(profile) / subject_type / subject_id


def ensure_subject(profile: str, subject_type: str, subject_id: str) -> Path:
    """Create the subject directory + minimal state.json if absent."""
    root = subject_root(profile, subject_type, subject_id)
    root.mkdir(parents=True, exist_ok=True)
    state_file = root / "state.json"
    if not state_file.exists():
        state_file.write_text(json.dumps({
            "subject_id": subject_id,
            "subject_type": subject_type,
            "created_at": _now(),
            "updated_at": _now(),
            "last_touch": None,
            "momentum": "fresh",
        }, indent=2), encoding="utf-8")
    return root


def read_state(profile: str, subject_type: str, subject_id: str) -> dict:
    """Return the parsed state.json, or {} if absent."""
    state_file = subject_root(profile, subject_type, subject_id) / "state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def update_state(
    profile: str, subject_type: str, subject_id: str,
    **fields,
) -> dict:
    """Patch state.json with the given fields. Always sets updated_at.
    Returns the new full state."""
    ensure_subject(profile, subject_type, subject_id)
    state = read_state(profile, subject_type, subject_id)
    state.update(fields)
    state["updated_at"] = _now()
    state_file = subject_root(profile, subject_type, subject_id) / "state.json"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def append_history(
    profile: str, subject_type: str, subject_id: str,
    entry: str, actor: str = "",
) -> None:
    """Append a timestamped entry to the subject's history.md."""
    ensure_subject(profile, subject_type, subject_id)
    hist = subject_root(profile, subject_type, subject_id) / "history.md"
    if not hist.exists():
        hist.write_text(f"# history — {subject_id}\n\n", encoding="utf-8")
    actor_tag = f" — {actor}" if actor else ""
    with open(hist, "a", encoding="utf-8") as f:
        f.write(f"\n_{_now()}{actor_tag}_\n\n{entry.rstrip()}\n")
    # Update last_touch in state.json
    update_state(profile, subject_type, subject_id, last_touch=_now())


def list_subjects(profile: str, subject_type: str) -> list[str]:
    """Return the list of subject_ids for a given (profile, subject_type)."""
    _validate_id(subject_type)
    parent = profile_vault(profile) / subject_type
    if not parent.exists():
        return []
    return sorted(p.name for p in parent.iterdir() if p.is_dir())


# ── Voice + profile docs (used primarily by Writing) ─────────────────────


def read_voice(profile: str, subject_type: str, subject_id: str) -> str:
    p = subject_root(profile, subject_type, subject_id) / "voice.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_voice(
    profile: str, subject_type: str, subject_id: str, content: str,
) -> None:
    ensure_subject(profile, subject_type, subject_id)
    p = subject_root(profile, subject_type, subject_id) / "voice.md"
    p.write_text(content, encoding="utf-8")


def read_profile(profile: str, subject_type: str, subject_id: str) -> str:
    p = subject_root(profile, subject_type, subject_id) / "profile.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_profile(
    profile: str, subject_type: str, subject_id: str, content: str,
) -> None:
    ensure_subject(profile, subject_type, subject_id)
    p = subject_root(profile, subject_type, subject_id) / "profile.md"
    p.write_text(content, encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "subject_root",
    "ensure_subject",
    "read_state",
    "update_state",
    "append_history",
    "list_subjects",
    "read_voice",
    "write_voice",
    "read_profile",
    "write_profile",
]
