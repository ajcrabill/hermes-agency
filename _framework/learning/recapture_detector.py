# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Recapture detector — the canary that catches a broken learning loop.

When the owner corrects something we've already been corrected on,
that's a structural failure: the previous rule didn't propagate to the
right skill, or the model isn't pulling injected rules into context,
or the rule was tagged wrong.

The detector runs INLINE at capture-time (not as a cron job). When a
new correction's embedding is similar enough to an existing one within
the lookback window, we:

  1. Record a row in `recapture_events`
  2. Emit a `recapture_detected` event (Sentinel sees this)
  3. The caller (typically `capture_correction`) returns the
     RecaptureResult; downstream wiring demotes the implicated skill
     and files a kanban alert.

Embedding model mismatch handling: if the new correction's embedder
differs from the prior rule's embedder (deployment swapped models),
we skip the comparison for that prior rule and emit a
`recapture-skipped-model-mismatch` event so Sentinel can warn the
operator. The new rule is still stored — it just doesn't trigger a
spurious recapture event against incompatible vectors.

Dismissal: the owner can mark a recapture as "not a recapture" via
the alert kanban task. We persist the (rule_a, rule_b) pair into
`recapture_denylist` so the detector excludes that exact pair from
future alerts. Other pairs involving either rule still fire normally.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .learning_db import decode_json_col, get_db
from .embeddings import Vector, cosine, deserialize


SIMILARITY_THRESHOLD = 0.85
LOOKBACK_DAYS = 90


@dataclass
class RecaptureResult:
    """Returned by check_recapture when a duplicate is detected."""

    new_rule_id: str
    similar_to: str             # the prior rule's id
    similarity: float
    skill_tags: list[str]       # union of the two rules' skill_tags
    detected_at: str


def check_recapture(
    new_rule_id: str,
    embedding: Vector | None = None,
    embedding_model: str | None = None,
    threshold: float = SIMILARITY_THRESHOLD,
    lookback_days: int = LOOKBACK_DAYS,
    db_path=None,
) -> RecaptureResult | None:
    """
    Compare the new rule's embedding against the last `lookback_days`
    of rules. If max similarity > threshold against an active rule
    using the same embedding model, persist a recapture_events row and
    return the RecaptureResult.

    Pass `embedding` and `embedding_model` to avoid an extra DB
    round-trip (correction_capture does this). Otherwise we load them
    from the new rule's row.

    Returns None if no recapture is detected.
    """
    db = get_db(path=db_path)
    try:
        # Load the new rule if embedding wasn't passed
        new_row = db.execute(
            "SELECT id, skill_tags, embedding, embedding_model, created_at "
            "FROM learning_rules WHERE id=?",
            (new_rule_id,),
        ).fetchone()
        if new_row is None:
            return None
        if embedding is None:
            embedding = deserialize(new_row["embedding"])
        if embedding_model is None:
            embedding_model = new_row["embedding_model"]
        new_skill_tags = decode_json_col(new_row["skill_tags"])

        if not embedding or not embedding_model:
            return None

        # Lookback window
        cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

        # Pull candidate prior rules — same embedding_model, active,
        # within window, not the rule itself, not denylisted with it.
        rows = db.execute(
            """
            SELECT lr.id, lr.skill_tags, lr.embedding, lr.embedding_model, lr.created_at
            FROM learning_rules lr
            WHERE lr.id != ?
              AND lr.status = 'active'
              AND lr.created_at >= ?
              AND lr.embedding_model = ?
              AND lr.embedding IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM recapture_denylist d
                  WHERE (d.rule_a = ? AND d.rule_b = lr.id)
                     OR (d.rule_a = lr.id AND d.rule_b = ?)
              )
            ORDER BY lr.created_at DESC
            """,
            (new_rule_id, cutoff, embedding_model, new_rule_id, new_rule_id),
        ).fetchall()

        best_match = None
        best_sim = 0.0
        best_skill_tags: list[str] = []

        for r in rows:
            prior_emb = deserialize(r["embedding"])
            if not prior_emb or len(prior_emb) != len(list(embedding)):
                continue
            sim = cosine(embedding, prior_emb)
            if sim > best_sim:
                best_sim = sim
                best_match = r["id"]
                best_skill_tags = decode_json_col(r["skill_tags"])

        if best_match is None or best_sim < threshold:
            return None

        # Persist the event
        now = datetime.now(timezone.utc).isoformat()
        union_tags = sorted(set(new_skill_tags) | set(best_skill_tags))

        db.execute(
            """
            INSERT INTO recapture_events (
                new_rule_id, similar_to, similarity, skill_tags, detected_at, notified
            ) VALUES (?, ?, ?, ?, ?, 0)
            """,
            (new_rule_id, best_match, float(best_sim),
             ",".join(union_tags), now),
        )
        db.commit()

        return RecaptureResult(
            new_rule_id=new_rule_id,
            similar_to=best_match,
            similarity=float(best_sim),
            skill_tags=union_tags,
            detected_at=now,
        )
    finally:
        db.close()


def dismiss_recapture(rule_a: str, rule_b: str, note: str = "", db_path=None) -> None:
    """
    Owner marked a (rule_a, rule_b) pair as 'not a recapture'. Persist
    to the denylist so the detector excludes the pair from future alerts.

    Records both orderings — (a, b) and (b, a) — so detector queries
    don't need to OR through alternatives.
    """
    now = datetime.now(timezone.utc).isoformat()
    db = get_db(path=db_path)
    try:
        for a, b in [(rule_a, rule_b), (rule_b, rule_a)]:
            db.execute(
                "INSERT OR REPLACE INTO recapture_denylist (rule_a, rule_b, added_at, note) "
                "VALUES (?, ?, ?, ?)",
                (a, b, now, note),
            )
        # Also mark any pending recapture_events between these two rules as dismissed
        db.execute(
            "UPDATE recapture_events SET dismissed=1, dismissal_note=? "
            "WHERE (new_rule_id=? AND similar_to=?) OR (new_rule_id=? AND similar_to=?)",
            (note, rule_a, rule_b, rule_b, rule_a),
        )
        db.commit()
    finally:
        db.close()


__all__ = [
    "RecaptureResult",
    "SIMILARITY_THRESHOLD",
    "LOOKBACK_DAYS",
    "check_recapture",
    "dismiss_recapture",
]
