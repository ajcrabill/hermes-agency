# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Per-subject state — the pattern used by:

  - Writing's per-author state (voice, project arc, history)
  - KB's per-coach state (session prep, instrument tracking)
  - BD's per-journalist + per-podcast state (relationship history)
  - Analyst's per-subject dossier state

One pattern, many uses. Each subject gets a namespaced directory:

  context/<profile>/<subject_type>/<subject_id>/
    state.json       lightweight metadata (last touch, momentum, etc.)
    voice.md         optional — voice profile for writing-support
    profile.md       longer-form context
    history.md       interaction log (appended on each touch)

The framework provides read/write helpers + the namespace guard
(so author A's writes can't accidentally land in author B's dir).

Public API:
  ensure_subject(profile, subject_type, subject_id)
  read_state(profile, subject_type, subject_id) → dict
  update_state(profile, subject_type, subject_id, **fields)
  append_history(profile, subject_type, subject_id, entry)
  list_subjects(profile, subject_type)
"""

from .store import (
    ensure_subject,
    read_state,
    update_state,
    append_history,
    list_subjects,
    read_profile,
    write_profile,
    read_voice,
    write_voice,
    subject_root,
)

__all__ = [
    "ensure_subject",
    "read_state",
    "update_state",
    "append_history",
    "list_subjects",
    "read_profile",
    "write_profile",
    "read_voice",
    "write_voice",
    "subject_root",
]
