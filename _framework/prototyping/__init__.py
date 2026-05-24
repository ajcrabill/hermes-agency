# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Prototyping flywheel — example-driven fast first draft + iteration.

The principle: time-to-prototype is the leading indicator of
time-to-final-content. Send examples (from anywhere) + audience +
purpose → fast first draft → iterative feedback. The flywheel:

  examples → style signature → first draft → feedback → revised
                                                          ↓
                              ↑ ← ← ← ← ← ← ← ← ← ← ← ← ← ←

Used primarily by Writing skills (newsletter, workbook, white-paper,
manuscript), but also CoS draft-composer and BD opportunistic-
outreach — anywhere "produce text in a particular style" is the job.

Public API:

  ingest_examples(sources)             → normalized text per source
  derive_style(texts)                   → StyleSignature
  start_prototype(name, audience, purpose, examples, ...) → prototype_id
  record_iteration(prototype_id, draft, feedback, change_summary)
  get_prototype(prototype_id)           → full history
  list_prototypes(profile=...)
"""

from .ingest import ingest_example, ingest_examples, IngestResult
from .style import derive_style, StyleSignature
from .iteration import (
    init_prototype_db,
    start_prototype,
    record_iteration,
    get_prototype,
    list_prototypes,
    mark_shipped,
    convergence_diagnostic,
    PrototypeRound,
)

__all__ = [
    "ingest_example", "ingest_examples", "IngestResult",
    "derive_style", "StyleSignature",
    "init_prototype_db", "start_prototype", "record_iteration",
    "get_prototype", "list_prototypes", "mark_shipped",
    "convergence_diagnostic", "PrototypeRound",
]
