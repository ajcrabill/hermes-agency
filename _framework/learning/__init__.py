# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Learning subsystem — the spine.

The seven-step learning loop (§1.1 of spec) lives here:

  1. CAPTURE       correction_capture.capture_correction()
  2. TAG           tag_resolver.resolve_tags()
  3. INJECT        rule_injection.inject_for_skill()
  4. APPLY         (the model uses the injected rule)
  5. RECORD        firings.record()
  6. RECAPTURE     recapture_detector.check_recapture()  (inline, at capture time)
  7. ESCALATE      autonomy.demote() + sentinel kanban alert  (delegated)

Every other subsystem (autonomy, verifier, kanban, send-guard,
sentinel) composes around this spine. Break any link and the owner is
re-teaching — and the system catches that as a structural failure.

Public functions (the stable surface):

  init_learning_db()         create schema if absent
  capture_correction(...)    main capture entry point
  inject_for_skill(...)      called at skill-load
  record_firing(...)         called when a rule influences a decision
  check_recapture(...)       called inline by capture_correction
  weekly_compliance_report() produces Sunday morning summary
"""

from .learning_db import init_learning_db, get_db
from .correction_capture import capture_correction
from .rule_injection import inject_for_skill
from .firings import record_firing
from .recapture_detector import check_recapture
from .tag_resolver import resolve_tags

__all__ = [
    "init_learning_db",
    "get_db",
    "capture_correction",
    "inject_for_skill",
    "record_firing",
    "check_recapture",
    "resolve_tags",
]
