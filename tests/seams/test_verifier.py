"""Verifier seam tests — registry + 10 criterion types."""

from __future__ import annotations

import sqlite3
import textwrap
from pathlib import Path

import pytest


@pytest.mark.seam
def test_registry_has_ten_types(tmp_agency):
    from _framework.verifier import list_types
    types = list_types()
    expected = {
        "file_exists", "file_contains", "file_not_contains",
        "sql_query",
        "kanban_status", "kanban_descendants_done",
        "learning_rule_recorded", "firing_recorded",
        "http_status", "shell_exit_zero",
    }
    assert expected.issubset(set(types))


@pytest.mark.seam
def test_no_criteria_fails_closed(tmp_agency):
    from _framework.verifier import check
    result = check([])
    assert not result.passed
    assert result.exit_code == 1


@pytest.mark.seam
def test_file_exists(tmp_path, tmp_agency):
    from _framework.verifier import check
    p = tmp_path / "marker.txt"
    p.write_text("hi")
    assert check([{"type": "file_exists", "args": {"path": str(p)}}]).passed
    assert not check([{"type": "file_exists", "args": {"path": str(tmp_path / "missing")}}]).passed


@pytest.mark.seam
def test_file_contains_and_not_contains(tmp_path, tmp_agency):
    from _framework.verifier import check
    p = tmp_path / "doc.md"
    p.write_text("# Title\n\nThe expected phrase is here.\n")
    assert check([{"type": "file_contains", "args": {"path": str(p), "needle": "expected phrase"}}]).passed
    assert not check([{"type": "file_contains", "args": {"path": str(p), "needle": "not present"}}]).passed
    assert check([{"type": "file_not_contains", "args": {"path": str(p), "needle": "forbidden word"}}]).passed
    assert not check([{"type": "file_not_contains", "args": {"path": str(p), "needle": "expected phrase"}}]).passed


@pytest.mark.seam
def test_sql_query(tmp_path, tmp_agency):
    from _framework.verifier import check
    db = tmp_path / "x.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("CREATE TABLE items(id INT); INSERT INTO items VALUES(1),(2),(3);")
    conn.commit()
    conn.close()
    assert check([{"type": "sql_query", "args": {"db": str(db), "query": "SELECT * FROM items", "expect_rows": 3}}]).passed
    assert not check([{"type": "sql_query", "args": {"db": str(db), "query": "SELECT * FROM items", "expect_rows": 5}}]).passed
    assert check([{"type": "sql_query", "args": {"db": str(db), "query": "SELECT * FROM items", "expect_min": 1, "expect_max": 10}}]).passed


@pytest.mark.seam
def test_learning_criteria_pass_after_capture(tmp_agency):
    from _framework.learning import capture_correction, record_firing
    from _framework.verifier import check

    r = capture_correction(
        correction="Yet another correction",
        source="cli:verifier-test",
        skill_tags=["test-skill"],
    )
    record_firing(r.rule_id, "test-skill", "loriah", action_summary="ok")
    assert check([{"type": "learning_rule_recorded", "args": {"source_contains": "verifier-test"}}]).passed
    assert check([{"type": "firing_recorded", "args": {"rule_id": r.rule_id, "skill_tag": "test-skill"}}]).passed


@pytest.mark.seam
def test_unknown_criterion_fails(tmp_agency):
    from _framework.verifier import check
    result = check([{"type": "totally-fake", "args": {}}])
    assert not result.passed
    assert any("unknown criterion type" in f.message for f in result.failures)
