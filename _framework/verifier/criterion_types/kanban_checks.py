# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""Kanban-based criteria: kanban_status, kanban_descendants_done."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from _framework.constants import KANBAN_DB
from _framework.verifier.registry import register


@register("kanban_status")
def kanban_status(args: dict) -> tuple[bool, str]:
    """args: { task_id: str, status: str }"""
    task_id = args.get("task_id")
    want = args.get("status")
    if not task_id or not want:
        return False, "args.task_id and args.status required"

    db_path = Path(str(args.get("db") or KANBAN_DB)).expanduser()
    if not db_path.exists():
        return False, f"kanban DB not found at {db_path}"
    try:
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        c.close()
    except Exception as e:
        return False, f"kanban query failed: {e}"
    if not row:
        return False, f"task {task_id} not in kanban"
    actual = row["status"]
    if actual == want:
        return True, f"task {task_id} status = {actual}"
    return False, f"task {task_id} status = {actual}, expected {want}"


@register("kanban_descendants_done")
def kanban_descendants_done(args: dict) -> tuple[bool, str]:
    """All `blocks`-linked descendants of the given task have status='done'.

    args: { task_id: str }
    """
    task_id = args.get("task_id")
    if not task_id:
        return False, "args.task_id required"

    db_path = Path(str(args.get("db") or KANBAN_DB)).expanduser()
    if not db_path.exists():
        return False, f"kanban DB not found at {db_path}"

    try:
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        # Walk the `blocks` graph downward
        seen = set()
        frontier = [task_id]
        not_done = []
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            children = c.execute(
                "SELECT child_id FROM task_links WHERE parent_id=? AND link_type='blocks'",
                (current,),
            ).fetchall()
            for r in children:
                cid = r["child_id"]
                frontier.append(cid)
                row = c.execute("SELECT status FROM tasks WHERE id=?", (cid,)).fetchone()
                if not row or row["status"] != "done":
                    not_done.append((cid, row["status"] if row else "missing"))
        c.close()
    except Exception as e:
        return False, f"kanban traversal failed: {e}"

    if not not_done:
        return True, f"all {len(seen) - 1} descendants of {task_id} are done"
    return False, f"{len(not_done)} descendant(s) not done: {not_done[:5]}"
