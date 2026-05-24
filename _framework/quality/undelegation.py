# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Auto-undelegation logic.

If a producer's rolling quality score drops below threshold across
N artifacts, propose undelegation — route their work back to a
lower-trust delegate or to the operator until trust is re-earned.

The framework PROPOSES; the operator (or a graduation-check skill)
decides. Auto-undelegation should never silently change who's doing
work — it surfaces the recommendation.

Trust levels:
  trusted     — rolling_score ≥ trust_threshold
  watching    — score below trust_threshold but above undelegation_threshold
  undelegated — score below undelegation_threshold; work shouldn't auto-
                route here

Defaults (operator-tunable via learning rules):
  window                  10 artifacts
  trust_threshold         0.80 — keep producing
  undelegation_threshold  0.65 — recommend undelegation
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .quality_db import rolling_score, producer_trust


DEFAULT_WINDOW = 10
DEFAULT_TRUST_THRESHOLD = 0.80
DEFAULT_UNDELEGATION_THRESHOLD = 0.65


@dataclass
class UndelegationVerdict:
    producer: str
    should_undelegate: bool
    proposed_state: str               # 'trusted' | 'watching' | 'undelegated'
    current_state: str
    rolling_score: float | None
    window: int
    reason: str
    transition: bool                  # True if proposed != current


def trust_level(
    producer: str,
    *,
    window: int = DEFAULT_WINDOW,
    trust_threshold: float = DEFAULT_TRUST_THRESHOLD,
    undelegation_threshold: float = DEFAULT_UNDELEGATION_THRESHOLD,
    db_path: Path | None = None,
) -> str:
    """Return the current proposed trust level based on rolling score."""
    roll = rolling_score(producer, window=window, db_path=db_path)
    score = roll.get("mean_score")
    if score is None or roll["count"] < max(3, window // 2):
        return "trusted"   # not enough data — default trusted
    if score >= trust_threshold:
        return "trusted"
    if score >= undelegation_threshold:
        return "watching"
    return "undelegated"


def should_undelegate(
    producer: str,
    *,
    window: int = DEFAULT_WINDOW,
    trust_threshold: float = DEFAULT_TRUST_THRESHOLD,
    undelegation_threshold: float = DEFAULT_UNDELEGATION_THRESHOLD,
    db_path: Path | None = None,
) -> UndelegationVerdict:
    """Compute the producer's verdict + propose a state transition.

    Note: this never auto-mutates `producer_trust`. The operator
    (via CoS or graduation-check) sees the verdict + decides.
    """
    roll = rolling_score(producer, window=window, db_path=db_path)
    current = producer_trust(producer, db_path=db_path).get("trust_state", "trusted")
    proposed = trust_level(
        producer, window=window,
        trust_threshold=trust_threshold,
        undelegation_threshold=undelegation_threshold,
        db_path=db_path,
    )
    score = roll.get("mean_score")
    reason = ""
    if score is None or roll["count"] < max(3, window // 2):
        reason = f"not enough data ({roll['count']} of {window} required); default trusted"
    elif proposed == "trusted":
        reason = f"rolling score {score:.2f} ≥ {trust_threshold} threshold"
    elif proposed == "watching":
        reason = (
            f"rolling score {score:.2f} below {trust_threshold} trust threshold "
            f"but above {undelegation_threshold} undelegation threshold"
        )
    else:
        reason = (
            f"rolling score {score:.2f} below {undelegation_threshold} "
            f"undelegation threshold across {roll['count']} artifacts"
        )

    return UndelegationVerdict(
        producer=producer,
        should_undelegate=(proposed == "undelegated"),
        proposed_state=proposed,
        current_state=current,
        rolling_score=score,
        window=roll["count"],
        reason=reason,
        transition=(proposed != current),
    )


__all__ = [
    "DEFAULT_WINDOW",
    "DEFAULT_TRUST_THRESHOLD",
    "DEFAULT_UNDELEGATION_THRESHOLD",
    "UndelegationVerdict",
    "trust_level",
    "should_undelegate",
]
