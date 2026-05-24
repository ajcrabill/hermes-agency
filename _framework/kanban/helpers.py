# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Framework-specific kanban helpers.

The framework's value-add over raw Hermes kanban:

  - `blocks` vs `tracks` link semantics (the schema_patch added the
    column; these helpers respect it).
  - `claim_task_for_skill` — the kanban-processor pattern: a skill
    finds work assigned to it that's ready (no unblocked `blocks`
    parents) and claims it atomically.
  - `complete_with_verifier` — close a task only when the verifier
    criteria pass; otherwise re-block with the failure reasons.
  - `blocking_parents` / `children` — graph traversal respecting
    link_type.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .integration import _conn, schema_patch_applied


@dataclass
class KanbanLink:
    parent_id: str
    child_id: str
    link_type: str  # 'blocks' | 'tracks'


def add_link(
    parent_id: str,
    child_id: str,
    link_type: str = "blocks",
    db_path: Path | None = None,
) -> None:
    """Add a link between two tasks. `link_type` must be 'blocks' or 'tracks'.

    Requires the schema patch — auto-applies it if missing.
    """
    if link_type not in ("blocks", "tracks"):
        raise ValueError(f"link_type must be 'blocks' or 'tracks', got {link_type!r}")
    if not schema_patch_applied(db_path):
        from .integration import apply_schema_patch
        apply_schema_patch(db_path)

    db = _conn(db_path)
    try:
        db.execute(
            "INSERT OR IGNORE INTO task_links (parent_id, child_id, link_type) VALUES (?, ?, ?)",
            (parent_id, child_id, link_type),
        )
        # If the row existed at default 'blocks' but we now want 'tracks' (or vice versa), update it.
        db.execute(
            "UPDATE task_links SET link_type=? WHERE parent_id=? AND child_id=?",
            (link_type, parent_id, child_id),
        )
        db.commit()
    finally:
        db.close()


def blocking_parents(task_id: str, db_path: Path | None = None) -> list[KanbanLink]:
    """Return parents linked to this task with link_type='blocks' — the
    only ones that gate completion. `tracks` parents are ignored."""
    db = _conn(db_path)
    try:
        # If the schema patch isn't applied yet, treat all links as blocks (Hermes default)
        if not _has_link_type_column(db):
            rows = db.execute(
                "SELECT parent_id, child_id FROM task_links WHERE child_id=?",
                (task_id,),
            ).fetchall()
            return [KanbanLink(parent_id=r["parent_id"], child_id=r["child_id"], link_type="blocks") for r in rows]
        rows = db.execute(
            "SELECT parent_id, child_id, link_type FROM task_links "
            "WHERE child_id=? AND link_type='blocks'",
            (task_id,),
        ).fetchall()
        return [KanbanLink(parent_id=r["parent_id"], child_id=r["child_id"], link_type=r["link_type"]) for r in rows]
    finally:
        db.close()


def children(task_id: str, link_type: str | None = None, db_path: Path | None = None) -> list[KanbanLink]:
    """Return children of this task. Filter by link_type if given."""
    db = _conn(db_path)
    try:
        has_col = _has_link_type_column(db)
        if has_col and link_type:
            rows = db.execute(
                "SELECT parent_id, child_id, link_type FROM task_links "
                "WHERE parent_id=? AND link_type=?",
                (task_id, link_type),
            ).fetchall()
        elif has_col:
            rows = db.execute(
                "SELECT parent_id, child_id, link_type FROM task_links WHERE parent_id=?",
                (task_id,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT parent_id, child_id FROM task_links WHERE parent_id=?",
                (task_id,),
            ).fetchall()
        out: list[KanbanLink] = []
        for r in rows:
            lt = r["link_type"] if has_col else "blocks"
            if link_type and lt != link_type:
                continue
            out.append(KanbanLink(parent_id=r["parent_id"], child_id=r["child_id"], link_type=lt))
        return out
    finally:
        db.close()


def _has_link_type_column(db: sqlite3.Connection) -> bool:
    cols = [r["name"] for r in db.execute("PRAGMA table_info(task_links)").fetchall()]
    return "link_type" in cols


# ── Claim / complete pattern ─────────────────────────────────────────────


def claim_task_for_skill(
    profile: str,
    skill: str,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """
    Atomic claim: find the highest-priority ready task assigned to
    `profile` that's tagged for `skill`, mark it claimed, return the
    row. Returns None if nothing is ready.

    A task is "ready" if status='ready' AND there's no `blocks` parent
    that isn't done. (`tracks` parents are aggregation-only and don't
    gate.)

    This is the kanban-processor primitive. Per-profile cron jobs call
    this every 5 minutes, do the work, then call `complete_with_verifier`.
    """
    db = _conn(db_path)
    try:
        has_link_type = _has_link_type_column(db)
        blocks_filter = "AND tl.link_type='blocks'" if has_link_type else ""

        # Find a candidate: ready, assigned to this profile, tagged for skill,
        # with no unfinished blocks-parents.
        row = db.execute(
            f"""
            SELECT t.* FROM tasks t
            WHERE t.assignee = ?
              AND t.status = 'ready'
              AND (t.skill = ? OR t.skill IS NULL)
              AND NOT EXISTS (
                  SELECT 1 FROM task_links tl
                  JOIN tasks p ON p.id = tl.parent_id
                  WHERE tl.child_id = t.id
                    {blocks_filter}
                    AND p.status != 'done'
              )
            ORDER BY t.priority DESC, t.created_at ASC
            LIMIT 1
            """,
            (profile, skill),
        ).fetchone()
        if not row:
            return None

        # Atomic CAS-style claim: only succeed if status is still 'ready'
        claim_lock = f"{profile}:{skill}:{int(time.time())}"
        cur = db.execute(
            "UPDATE tasks SET status='claimed', claim_lock=? WHERE id=? AND status='ready'",
            (claim_lock, row["id"]),
        )
        db.commit()
        if cur.rowcount == 0:
            # Lost the race; try again later.
            return None
        return dict(row)
    finally:
        db.close()


def complete_with_verifier(
    task_id: str,
    verifier_criteria: list[dict[str, Any]],
    db_path: Path | None = None,
) -> dict[str, Any]:
    """
    Run the task's verifier criteria. On pass: set status='done'. On
    fail: set status='blocked' with the failure reasons in a comment.

    Returns: {'passed': bool, 'failures': [...]}
    """
    from _framework.verifier import check as verifier_check

    result = verifier_check(verifier_criteria)
    db = _conn(db_path)
    try:
        if result.passed:
            db.execute(
                "UPDATE tasks SET status='done', completed_at=? WHERE id=?",
                (int(time.time()), task_id),
            )
            db.execute(
                "INSERT INTO task_comments (task_id, author, body, created_at) "
                "VALUES (?, 'verifier', ?, ?)",
                (task_id, f"verifier passed ({result.n_criteria} criteria)", int(time.time())),
            )
            db.commit()
            return {"passed": True, "failures": []}

        # Block on failure
        failure_text = "\n".join(f"  - [{f.type}] {f.message}" for f in result.failures)
        body = f"verifier blocked completion:\n{failure_text}"
        db.execute("UPDATE tasks SET status='blocked' WHERE id=?", (task_id,))
        db.execute(
            "INSERT INTO task_comments (task_id, author, body, created_at) "
            "VALUES (?, 'verifier', ?, ?)",
            (task_id, body, int(time.time())),
        )
        db.commit()
        return {
            "passed": False,
            "failures": [{"type": f.type, "message": f.message, "args": f.args} for f in result.failures],
        }
    finally:
        db.close()


__all__ = [
    "KanbanLink",
    "add_link",
    "blocking_parents",
    "children",
    "claim_task_for_skill",
    "complete_with_verifier",
]
