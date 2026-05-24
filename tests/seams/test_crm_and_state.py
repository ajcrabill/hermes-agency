"""Tests for the new substrate modules: CRM (with 4-priority reply matching)
and per-subject state."""

from __future__ import annotations

import pytest


# ── CRM ─────────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_crm_init_and_lead_add(tmp_agency):
    from _framework.crm import add_lead, list_leads
    lead_id = add_lead(name="Acme School District", primary_email="sup@acme.edu", source="news-driven")
    assert lead_id > 0
    leads = list_leads()
    assert len(leads) == 1
    assert leads[0]["name"] == "Acme School District"


@pytest.mark.seam
def test_crm_contact_with_alternates(tmp_agency):
    from _framework.crm import add_contact, find_contact_by_email
    cid = add_contact(
        name="J Smith",
        email="j.smith@acme.edu",
        alternate_emails=["jsmith@personal.com", "j.smith.work@acme.edu"],
    )
    assert find_contact_by_email("j.smith@acme.edu")["id"] == cid
    assert find_contact_by_email("jsmith@personal.com")["id"] == cid
    assert find_contact_by_email("j.smith.work@acme.edu")["id"] == cid
    assert find_contact_by_email("unknown@example.com") is None


@pytest.mark.seam
def test_reply_matcher_priority_1_thread(tmp_agency):
    from _framework.crm import add_lead, log_sent_thread, match_reply
    lid = add_lead(name="Acme", primary_email="sup@acme.edu")
    log_sent_thread(thread_id="th_001", lead_id=lid, subject="Re: Effective Boards")
    m = match_reply(from_email="anyone@whatever.com", thread_id="th_001")
    assert m.priority == 1
    assert m.matched
    assert m.lead_id == lid


@pytest.mark.seam
def test_reply_matcher_priority_2_email(tmp_agency):
    from _framework.crm import add_lead, add_contact, match_reply
    lid = add_lead(name="Acme", primary_email="sup@acme.edu")
    add_contact(name="J Smith", email="alt@acme.edu", lead_id=lid)
    m = match_reply(from_email="alt@acme.edu")
    assert m.priority == 2
    assert m.matched
    assert m.lead_id == lid


@pytest.mark.seam
def test_reply_matcher_priority_3_domain_unique(tmp_agency):
    from _framework.crm import add_lead, match_reply
    lid = add_lead(name="Acme", primary_email="sup@acme.edu")
    m = match_reply(from_email="random@acme.edu")
    assert m.priority == 3
    assert m.matched
    assert m.lead_id == lid


@pytest.mark.seam
def test_reply_matcher_priority_3_domain_ambiguous(tmp_agency):
    from _framework.crm import add_lead, match_reply
    add_lead(name="Acme East", primary_email="sup1@acme.edu")
    add_lead(name="Acme West", primary_email="sup2@acme.edu")
    m = match_reply(from_email="someone@acme.edu")
    assert m.priority == 3
    assert m.matched
    assert m.lead_id is None   # ambiguous — caller decides
    assert len(m.domain_candidates) == 2


@pytest.mark.seam
def test_reply_matcher_priority_4_unmatched(tmp_agency):
    from _framework.crm import match_reply
    m = match_reply(from_email="stranger@nowhere.org", thread_id="th_unknown")
    assert m.priority == 4
    assert not m.matched


@pytest.mark.seam
def test_log_reply_records_priority(tmp_agency):
    from _framework.crm import add_lead, log_reply, find_recent_replies
    lid = add_lead(name="Acme", primary_email="sup@acme.edu")
    log_reply(
        from_email="sup@acme.edu", lead_id=lid,
        subject="Re: pitch", sentiment="positive",
        match_priority=2,
    )
    replies = find_recent_replies(lead_id=lid)
    assert len(replies) == 1
    assert replies[0]["sentiment"] == "positive"
    assert replies[0]["match_priority"] == 2


# ── Per-subject state ───────────────────────────────────────────────────


@pytest.mark.seam
def test_subject_namespace_guard(tmp_agency):
    from _framework.per_subject_state import ensure_subject
    # These should all raise — path-escape attempts
    import pytest
    for bad_id in ("../escape", "/abs", ".hidden", "with space"):
        with pytest.raises(ValueError):
            ensure_subject("loriah", "authors", bad_id)


@pytest.mark.seam
def test_subject_state_lifecycle(tmp_agency):
    from _framework.per_subject_state import (
        ensure_subject, read_state, update_state,
        read_voice, write_voice,
        append_history, list_subjects,
    )

    ensure_subject("libra", "authors", "jane-doe")
    state = read_state("libra", "authors", "jane-doe")
    assert state["subject_id"] == "jane-doe"
    assert state["subject_type"] == "authors"

    update_state("libra", "authors", "jane-doe", momentum="active", word_count=15000)
    state = read_state("libra", "authors", "jane-doe")
    assert state["momentum"] == "active"
    assert state["word_count"] == 15000

    write_voice("libra", "authors", "jane-doe",
                "Voice: short sentences. Active verbs. Light on adjectives.")
    voice = read_voice("libra", "authors", "jane-doe")
    assert "short sentences" in voice

    append_history(
        "libra", "authors", "jane-doe",
        "Sent draft of Chapter 4. Author responded with two notes.",
        actor="libra",
    )
    state_after = read_state("libra", "authors", "jane-doe")
    assert state_after["last_touch"] is not None

    subjects = list_subjects("libra", "authors")
    assert "jane-doe" in subjects


@pytest.mark.seam
def test_subject_isolation_between_subjects(tmp_agency):
    """Writing to subject A doesn't affect subject B."""
    from _framework.per_subject_state import write_voice, read_voice
    write_voice("libra", "authors", "alice", "Alice voice: literary.")
    write_voice("libra", "authors", "bob",   "Bob voice: technical.")
    assert "literary" in read_voice("libra", "authors", "alice")
    assert "technical" in read_voice("libra", "authors", "bob")
    assert "literary" not in read_voice("libra", "authors", "bob")
