# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Two-tier quality auditor.

The verifier (§6.1) is the binary gate: criteria pass or completion
is refused. This module adds a *continuous* score (0.0-1.0 per
dimension) and the auto-undelegation pattern from agent-core: when
a producer's rolling quality score drops below threshold across N
artifacts, work routes back to a lower-trust delegate (or the
operator) until trust is re-earned.

Two layers compose:

  - **Verifier** (existing, binary) — "is this complete?"
  - **Quality scorer** (this module, continuous) — "how well?"

Both run at completion time. The verifier blocks; the quality
scorer logs + triggers undelegation when patterns emerge.

Schema (`quality.db`):
  scored_artifacts    one row per (artifact, producer, scored_at)
                      with per-dimension scores
  producer_trust      rolling trust score per producer, updated on
                      every score below threshold

Public API:

  score_artifact(producer, artifact_id, dimensions={...}, notes=...)
  rolling_score(producer, window=10)
  should_undelegate(producer, threshold=0.65) → bool + reason
  trust_level(producer) → "trusted" | "watching" | "undelegated"
"""

from .quality_db import (
    init_quality_db,
    score_artifact,
    list_scores,
    rolling_score,
    producer_trust,
    set_producer_trust,
    ScoredArtifact,
)
from .undelegation import (
    should_undelegate,
    trust_level,
    UndelegationVerdict,
)

__all__ = [
    "init_quality_db",
    "score_artifact",
    "list_scores",
    "rolling_score",
    "producer_trust",
    "set_producer_trust",
    "ScoredArtifact",
    "should_undelegate",
    "trust_level",
    "UndelegationVerdict",
]
