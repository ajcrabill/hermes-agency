# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Coaching subsystem — the missing manuscript creation centerpiece.

Generalized from v7's book_coaching workflow ("Scribe Method"). The
framework provides the *substrate* — schema, ingestion, transcription,
three-editor pipeline. The *methodology* (phase names, question
templates, depth calibration) is operator-customized.

Architecture: this subsystem uses the **no_agent cron** pattern —
a self-contained script handles the entire decision loop (poll
email, classify response, generate next questions, store, send),
calling the inference API as a TOOL for question generation rather
than handing decisions to an LLM cron agent. This is the v7 lesson
learned the hard way: LLMs with DB write access become "creative"
about state.

Schema (`_framework/coaching/coaching_db.py`):
  users            — author identified by email (PK)
  projects         — generic for books / theses / screenplays / etc.
  phases           — methodology-defined sequence
  qa_history       — Q&A by phase, with answer_source tagged
  deliverables     — outputs per phase
  ingested_files   — attachment dedup via sha256

Public API:
  init_coaching_db()
  add_user / find_user_by_email
  add_project / find_project / list_active_projects
  record_qa / get_open_questions
  log_deliverable
  log_ingested_file (dedup by sha256)

The three editor lenses (polish / structural / voice) are skills
that operate on text and return scored verdicts, not state managers.
"""

from .coaching_db import (
    init_coaching_db,
    add_user, find_user_by_email,
    add_project, find_project, list_active_projects,
    advance_phase,
    record_qa, get_open_questions, get_qa_history, answer_question,
    log_deliverable, list_deliverables,
    log_ingested_file, find_ingested_file,
)

__all__ = [
    "init_coaching_db",
    "add_user", "find_user_by_email",
    "add_project", "find_project", "list_active_projects", "advance_phase",
    "record_qa", "get_open_questions", "get_qa_history", "answer_question",
    "log_deliverable", "list_deliverables",
    "log_ingested_file", "find_ingested_file",
]
