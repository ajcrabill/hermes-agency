# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Bridge between HermesAgency and Hermes' kanban_db.

Hermes manages the kanban DB schema, CRUD, and dispatch — we don't
duplicate any of that. We only:

  1. Resolve the active board's DB path with the same lookup order
     Hermes uses (env vars, board-current, default fallback)
  2. Apply an additive schema patch that adds `task_links.link_type`
     defaulting to 'blocks' (preserves Hermes' prior behavior on
     existing rows)
  3. Provide a small set of framework-specific helpers for the
     `blocks`/`tracks` distinction

The patch is applied idempotently. Running it twice is safe. The
patch is also a no-op against a Hermes that has merged the upstream
support for `link_type` (which is the eventual goal of the PR).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from _framework.constants import AGENCY_HOME, KANBAN_DB


# ── Active board resolution ─────────────────────────────────────────────
# Mirrors Hermes' lookup order (kanban_db.py top-of-file docs).


def active_kanban_db() -> Path:
    """Return the path to the active kanban DB.

    Resolution order (highest precedence first):
      1. HERMES_KANBAN_DB env var
      2. HERMES_KANBAN_BOARD env var → ~/.hermes/kanban/boards/<board>/kanban.db
      3. <hermes_root>/kanban/current file → board name → kanban/boards/<board>/kanban.db
      4. AGENCY_HOME/kanban.db (preferred when running inside an .agency deployment)
      5. ~/.hermes/kanban.db (Hermes default)
    """
    # 1. Explicit env-var pin
    explicit = os.environ.get("HERMES_KANBAN_DB")
    if explicit:
        return Path(explicit).expanduser()

    # 2. Board env var
    hermes_root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    board = os.environ.get("HERMES_KANBAN_BOARD")
    if board and board != "default":
        return hermes_root / "kanban" / "boards" / board / "kanban.db"

    # 3. Board-current pointer
    current_file = hermes_root / "kanban" / "current"
    if current_file.exists():
        slug = current_file.read_text(encoding="utf-8", errors="replace").strip()
        if slug and slug != "default":
            return hermes_root / "kanban" / "boards" / slug / "kanban.db"

    # 4. Agency deployment-local kanban (if it exists)
    agency_local = AGENCY_HOME / "kanban.db"
    if agency_local.exists():
        return agency_local

    # 5. Hermes default
    return hermes_root / "kanban.db"


def _conn(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or active_kanban_db()
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


# ── Schema patch: add link_type to task_links ───────────────────────────


SCHEMA_PATCH_SQL = """
-- Additive: existing rows default to 'blocks' (Hermes' prior behavior).
ALTER TABLE task_links ADD COLUMN link_type TEXT NOT NULL DEFAULT 'blocks';
CREATE INDEX IF NOT EXISTS idx_links_type ON task_links(link_type);
"""


def schema_patch_applied(db_path: Path | None = None) -> bool:
    """True if the link_type column already exists on task_links."""
    db = _conn(db_path)
    try:
        cols = [r["name"] for r in db.execute("PRAGMA table_info(task_links)").fetchall()]
        return "link_type" in cols
    finally:
        db.close()


def apply_schema_patch(db_path: Path | None = None) -> bool:
    """Idempotent: add the link_type column if absent. Returns True if a
    change was made, False if no-op (already present)."""
    if schema_patch_applied(db_path):
        return False
    db = _conn(db_path)
    try:
        db.executescript(SCHEMA_PATCH_SQL)
        db.commit()
        return True
    finally:
        db.close()


__all__ = [
    "active_kanban_db",
    "apply_schema_patch",
    "schema_patch_applied",
    "SCHEMA_PATCH_SQL",
]
