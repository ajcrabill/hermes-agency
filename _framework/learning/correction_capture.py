# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Correction capture — the entry point for the learning loop.

Every owner correction lands here. Side effects:

- persists to `learning_rules`
- embeds the correction with the deployment-configured embedder
- runs recapture detection against the last 90 days
- emits a `correction_captured` event (Sentinel reads via events.db)
- if recapture detected: emits `recapture_detected` event +
  triggers downstream demotion of the responsible skill (caller's
  responsibility — capture returns the recapture result)

The capture function is the FIRST link in the seven-step learning
loop. If it breaks, every owner correction is lost; the system can
never learn. Treat it accordingly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .learning_db import (
    encode_json_col,
    get_db,
)
from .embeddings import get_embedder, serialize
from .tag_resolver import resolve_tags
from .recapture_detector import RecaptureResult, check_recapture


@dataclass
class CaptureResult:
    rule_id: str
    skill_tags: list[str]
    role_tags: list[str]
    voice_tags: list[str]
    is_hard: bool
    embedding_model: str
    recapture: RecaptureResult | None
    tag_issues: list[str]
    goal_keys: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.goal_keys is None:
            self.goal_keys = []


def capture_correction(
    correction: str,
    source: str,
    skill_tags: list[str],
    role_tags: list[str] | None = None,
    voice_tags: list[str] | None = None,
    is_hard: bool = False,
    notes: str | None = None,
    goal_keys: list[str] | None = None,
    db_path=None,
) -> CaptureResult:
    """
    Capture an owner correction into the learning corpus.

    Returns a CaptureResult with the new rule_id and any recapture
    detection. Callers are responsible for acting on the recapture
    (demoting skills, filing kanban alerts) — capture itself only
    persists + detects.

    `goal_keys` (v0.23.8+) — optional list of strategic-alignment keys
    the correction is tied to. Keys take three forms:

      - `O<N>`             — an Outcome (e.g. "O1")
      - `IG<N.M>`          — an Interim Goal (e.g. "IG1.1")
      - `skill:<path>`     — an Initiative skill (e.g. "skill:devon/lookalike-prospect-builder")
      - `script:<path>`    — an Initiative script (e.g. "script:devon/pipeline-watchdog.py")

    Most corrections are stylistic and won't carry goal_keys. The
    flag is for corrections where the link matters (e.g. "stop CCing
    Spencer on outreach emails" specifically applies to Initiative
    `devon/cold-outreach-sender`).

    Raises ValueError on malformed input (empty correction, empty
    skill_tags after normalization, etc.).
    """
    if not correction or not correction.strip():
        raise ValueError("correction is empty")
    if not source or not source.strip():
        raise ValueError("source is required")

    tags = resolve_tags(
        skill_tags=skill_tags,
        role_tags=role_tags,
        voice_tags=voice_tags,
    )
    if not tags.skill_tags:
        raise ValueError(
            f"At least one skill_tag is required (use 'general' for cross-skill). Issues: {tags.issues}"
        )

    normalized_goal_keys = _normalize_goal_keys(goal_keys)

    rule_id = _make_rule_id(correction, source)
    now = _now_iso()

    embedder = get_embedder()
    embedding = embedder.embed(correction)
    embedding_blob = serialize(embedding)

    db = get_db(path=db_path)
    try:
        db.execute(
            """
            INSERT INTO learning_rules (
                id, correction, source,
                skill_tags, role_tags, voice_tags, goal_keys,
                is_hard, status, embedding, embedding_model,
                created_at, updated_at, notes
            ) VALUES (?, ?, ?,  ?, ?, ?, ?,  ?, 'active', ?, ?,  ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                rule_id, correction.strip(), source.strip(),
                encode_json_col(tags.skill_tags),
                encode_json_col(tags.role_tags),
                encode_json_col(tags.voice_tags),
                encode_json_col(normalized_goal_keys) if normalized_goal_keys else None,
                1 if is_hard else 0,
                embedding_blob, embedder.name,
                now, now, notes or "",
            ),
        )
        db.commit()
    finally:
        db.close()

    # Recapture detection runs in-line on a fresh connection (so the new
    # rule is visible during the lookback scan).
    recapture = check_recapture(rule_id, embedding=embedding, embedding_model=embedder.name, db_path=db_path)

    return CaptureResult(
        rule_id=rule_id,
        skill_tags=tags.skill_tags,
        role_tags=tags.role_tags,
        voice_tags=tags.voice_tags,
        is_hard=is_hard,
        embedding_model=embedder.name,
        recapture=recapture,
        tag_issues=tags.issues,
        goal_keys=normalized_goal_keys,
    )


# ── Convenience wrappers (spec §3.2) ─────────────────────────────────────


def capture_from_kanban_comment(task_id: str, comment_text: str, skill_tags: list[str], **kwargs: Any) -> CaptureResult:
    """Owner replied to a kanban task with a correction."""
    return capture_correction(
        correction=comment_text,
        source=f"kanban:{task_id}",
        skill_tags=skill_tags,
        **kwargs,
    )


def capture_from_inbox(message_id: str, classification: str, correction: str, skill_tags: list[str], **kwargs: Any) -> CaptureResult:
    """Owner email contained a directive that was classified as a learning."""
    return capture_correction(
        correction=correction,
        source=f"inbox:{message_id}:{classification}",
        skill_tags=skill_tags,
        **kwargs,
    )


def capture_from_chat(session_id: str, turn_index: int, correction: str, skill_tags: list[str], **kwargs: Any) -> CaptureResult:
    """Interactive correction during a Hermes chat."""
    return capture_correction(
        correction=correction,
        source=f"chat:{session_id}:turn-{turn_index}",
        skill_tags=skill_tags,
        **kwargs,
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_GOAL_KEY_PREFIXES = ("O", "IG", "skill:", "script:")


def _normalize_goal_keys(raw: list[str] | None) -> list[str]:
    """Strip + deduplicate + validate the prefix shape.

    Accepts None or []; returns []. Accepts a list of keys; returns
    them deduplicated (preserving first occurrence). Keys that don't
    match the four known prefixes are kept verbatim — the audit's
    `goal-attribution-shape` rule can flag them; we don't reject at
    capture time (would lose corrections to a typo).
    """
    if not raw:
        return []
    seen = set()
    out = []
    for k in raw:
        if not k or not isinstance(k, str):
            continue
        k = k.strip()
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def _make_rule_id(correction: str, source: str) -> str:
    """
    Stable hash of (correction, source). Same correction from same source
    de-duplicates rather than recapturing. Different sources = different
    rules (intentional: "AJ said this in inbox" vs "AJ said this in chat"
    are tracked separately).
    """
    h = hashlib.sha256()
    h.update(correction.strip().encode("utf-8"))
    h.update(b"|")
    h.update(source.strip().encode("utf-8"))
    return h.hexdigest()[:12]


__all__ = [
    "CaptureResult",
    "capture_correction",
    "capture_from_kanban_comment",
    "capture_from_inbox",
    "capture_from_chat",
]
