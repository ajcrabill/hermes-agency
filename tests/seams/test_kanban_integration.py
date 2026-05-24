"""Kanban integration tests — schema patch + link semantics + claim/complete."""

from __future__ import annotations

import sqlite3
import time

import pytest


def _stub_hermes_kanban(tmp_agency, db_name="kanban.db"):
    """Create a minimal Hermes-shaped kanban DB so we can test the patch."""
    db = tmp_agency / db_name
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT,
            assignee TEXT,
            skill TEXT,
            status TEXT NOT NULL DEFAULT 'ready',
            priority INTEGER NOT NULL DEFAULT 0,
            claim_lock TEXT,
            created_at INTEGER NOT NULL,
            completed_at INTEGER
        );
        CREATE TABLE task_links (
            parent_id TEXT NOT NULL,
            child_id TEXT NOT NULL,
            PRIMARY KEY (parent_id, child_id)
        );
        CREATE TABLE task_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db


@pytest.mark.seam
def test_schema_patch_is_idempotent(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))

    from _framework.kanban import apply_schema_patch, schema_patch_applied
    assert schema_patch_applied() is False
    assert apply_schema_patch() is True   # first apply: change made
    assert schema_patch_applied() is True
    assert apply_schema_patch() is False  # second apply: no-op


@pytest.mark.seam
def test_add_link_with_blocks_default(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))
    from _framework.kanban import add_link, blocking_parents, children

    # Seed tasks
    conn = sqlite3.connect(str(db))
    conn.executemany(
        "INSERT INTO tasks (id, title, status, created_at) VALUES (?, ?, 'ready', ?)",
        [("parent", "P", int(time.time())), ("child", "C", int(time.time()))],
    )
    conn.commit()
    conn.close()

    add_link("parent", "child")  # defaults to blocks
    blocking = blocking_parents("child")
    assert len(blocking) == 1
    assert blocking[0].parent_id == "parent"
    assert blocking[0].link_type == "blocks"

    kids = children("parent")
    assert len(kids) == 1


@pytest.mark.seam
def test_tracks_link_does_not_block(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))
    from _framework.kanban import add_link, blocking_parents

    conn = sqlite3.connect(str(db))
    conn.executemany(
        "INSERT INTO tasks (id, title, status, created_at) VALUES (?, ?, 'ready', ?)",
        [("umbrella", "U", int(time.time())), ("worker", "W", int(time.time()))],
    )
    conn.commit()
    conn.close()

    add_link("umbrella", "worker", link_type="tracks")
    blocking = blocking_parents("worker")
    # The tracks link should NOT appear in blocking_parents
    assert blocking == []


@pytest.mark.seam
def test_claim_task_atomic(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))
    from _framework.kanban import claim_task_for_skill

    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO tasks (id, title, assignee, skill, status, priority, created_at) "
        "VALUES ('t1', 'Test task', 'loriah', 'draft-composer', 'ready', 5, ?)",
        (int(time.time()),),
    )
    conn.commit()
    conn.close()

    claimed = claim_task_for_skill(profile="loriah", skill="draft-composer")
    assert claimed is not None
    assert claimed["id"] == "t1"

    # Second claim should return None (task is no longer 'ready')
    again = claim_task_for_skill(profile="loriah", skill="draft-composer")
    assert again is None


@pytest.mark.seam
def test_claim_respects_blocking_parents(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))
    from _framework.kanban import add_link, claim_task_for_skill

    conn = sqlite3.connect(str(db))
    conn.executemany(
        "INSERT INTO tasks (id, title, assignee, skill, status, created_at) VALUES (?, ?, 'loriah', 'compose', ?, ?)",
        [
            ("parent", "Parent", "ready", int(time.time())),
            ("child", "Child", "ready", int(time.time())),
        ],
    )
    conn.commit()
    conn.close()

    add_link("parent", "child", link_type="blocks")

    # Child shouldn't be claimable while parent is not done
    claimed = claim_task_for_skill(profile="loriah", skill="compose")
    # The parent is also ready and claimable; the child is blocked. We
    # should claim the parent.
    assert claimed is not None
    assert claimed["id"] == "parent"


@pytest.mark.seam
def test_complete_with_verifier_passes(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))
    from _framework.kanban import complete_with_verifier

    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO tasks (id, title, status, created_at) VALUES ('t-pass', 'Pass me', 'claimed', ?)",
        (int(time.time()),),
    )
    conn.commit()
    conn.close()

    marker = tmp_agency / "marker.txt"
    marker.write_text("done")
    criteria = [{"type": "file_exists", "args": {"path": str(marker)}}]
    result = complete_with_verifier("t-pass", criteria)
    assert result["passed"] is True

    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT status FROM tasks WHERE id='t-pass'").fetchone()
    conn.close()
    assert row[0] == "done"


@pytest.mark.seam
def test_complete_with_verifier_blocks_on_failure(tmp_agency, monkeypatch):
    db = _stub_hermes_kanban(tmp_agency)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db))
    from _framework.kanban import complete_with_verifier

    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO tasks (id, title, status, created_at) VALUES ('t-fail', 'Fail me', 'claimed', ?)",
        (int(time.time()),),
    )
    conn.commit()
    conn.close()

    criteria = [{"type": "file_exists", "args": {"path": "/nonexistent/path/marker.txt"}}]
    result = complete_with_verifier("t-fail", criteria)
    assert result["passed"] is False
    assert result["failures"]

    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT status FROM tasks WHERE id='t-fail'").fetchone()
    conn.close()
    assert row[0] == "blocked"
