"""Coaching subsystem tests — schema, users, projects, Q&A, ingest dedup."""

from __future__ import annotations

import pytest


@pytest.mark.seam
def test_user_upsert(tmp_agency):
    from _framework.coaching import add_user, find_user_by_email
    uid1 = add_user(email="author@example.com", name="Jane Author")
    uid2 = add_user(email="author@example.com", name="Different name same email")
    assert uid1 == uid2   # upsert by email
    u = find_user_by_email("author@example.com")
    assert u["name"] == "Jane Author"   # first insert sticks


@pytest.mark.seam
def test_project_lifecycle(tmp_agency):
    from _framework.coaching import (
        add_user, add_project, find_project, list_active_projects, advance_phase,
    )
    uid = add_user(email="author@example.com", name="Jane")
    pid = add_project(
        user_id=uid, title="The 50% Journey",
        project_type="book", methodology="scribe-method",
        short_name="50pj",
    )
    proj = find_project(pid)
    assert proj["phase"] == 1
    assert proj["methodology"] == "scribe-method"

    active = list_active_projects()
    assert any(p["id"] == pid for p in active)

    new_phase = advance_phase(pid)
    assert new_phase == 2
    proj = find_project(pid)
    assert proj["phase"] == 2

    advance_phase(pid, to_phase=5)
    proj = find_project(pid)
    assert proj["phase"] == 5


@pytest.mark.seam
def test_qa_history_open_and_answered(tmp_agency):
    from _framework.coaching import (
        add_user, add_project, record_qa, get_open_questions,
        get_qa_history, answer_question,
    )
    uid = add_user(email="a@example.com")
    pid = add_project(user_id=uid, title="Book")
    q1 = record_qa(project_id=pid, phase_number=1, question="Q1")
    q2 = record_qa(project_id=pid, phase_number=1, question="Q2",
                    answer="A2", answer_source="voice")
    open_qs = get_open_questions(pid)
    assert len(open_qs) == 1
    assert open_qs[0]["id"] == q1

    answer_question(q1, "A1", answer_source="typed")
    assert len(get_open_questions(pid)) == 0

    full = get_qa_history(pid)
    assert len(full) == 2


@pytest.mark.seam
def test_ingested_file_dedup_by_sha(tmp_agency):
    from _framework.coaching import log_ingested_file, find_ingested_file
    first = log_ingested_file(
        sha256="abc123" * 10, filename="chapter1.docx", chars=5000,
        source_msg_id="msg-001",
    )
    assert first is not None
    second = log_ingested_file(
        sha256="abc123" * 10, filename="chapter1-resent.docx", chars=5000,
        source_msg_id="msg-002",
    )
    assert second is None   # dedup hit
    found = find_ingested_file("abc123" * 10)
    assert found["filename"] == "chapter1.docx"   # first one stuck


@pytest.mark.seam
def test_deliverables_logged(tmp_agency):
    from _framework.coaching import (
        add_user, add_project, log_deliverable, list_deliverables,
    )
    uid = add_user(email="a@example.com")
    pid = add_project(user_id=uid, title="Book")
    log_deliverable(project_id=pid, phase_number=2, name="discovery-summary",
                    file_path="/tmp/discovery.md", version=1)
    log_deliverable(project_id=pid, phase_number=2, name="discovery-summary",
                    file_path="/tmp/discovery-v2.md", version=2)
    rows = list_deliverables(pid)
    assert len(rows) == 2
    assert rows[1]["version"] == 2


@pytest.mark.seam
def test_paused_project_excluded(tmp_agency):
    """A paused project (paused_until in the future) drops out of
    list_active_projects."""
    from _framework.coaching.coaching_db import _conn, _now
    from _framework.coaching import add_user, add_project, list_active_projects
    from datetime import datetime, timedelta, timezone

    uid = add_user(email="x@example.com")
    pid = add_project(user_id=uid, title="Paused Book")
    future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    db = _conn()
    db.execute("UPDATE projects SET paused_until=? WHERE id=?", (future, pid))
    db.commit()
    db.close()

    active = list_active_projects()
    assert not any(p["id"] == pid for p in active)
