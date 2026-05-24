"""Tier 3 interview tests — scripted prompter generates real doc drafts."""

from __future__ import annotations

import pytest


def _scripted_prompter(answers: dict[str, str]):
    """Return a prompter that maps question.key -> answer."""

    def _p(question):
        return answers.get(question.key, "skip" if question.optional else "")

    return _p


@pytest.mark.seam
def test_interview_writes_all_five_docs(tmp_agency):
    from _framework.ops.init.tier3_interview import run_tier3_interview
    from _framework.constants import (
        GOALS_MD, VALUES_MD, PERSONAL_MD, WORK_MD, CLIENTS_MD,
    )

    answers = {
        # Goals
        "MISSION_STATEMENT": "Help small agencies stop re-teaching their AI.",
        "ANNUAL_GOALS": "1) ship v0.1\n2) onboard 3 deployments\n3) document migration path",
        "ACTIVE_PROJECTS": "HermesAgency framework build",
        "EXPLICIT_NON_GOALS": "Not building yet another single-agent assistant",
        # Values
        "CORE_VALUES": "Truth over comfort. Craft over volume.",
        "WORK_QUALITY_STANDARDS": "Concrete, verifiable, source-cited.",
        "KEY_RELATIONSHIPS": "Family first; longtime collaborators second; clients third.",
        "INTERPERSONAL_PRINCIPLES": "Direct, warm, assume good intent.",
        "NON_NEGOTIABLES": "Never inline secrets. Never spam.",
        # Personal — all optional, skip most
        "WORK_LIFE_BOUNDARIES": "No work after 7pm Central.",
        # Work
        "AGENCY_OFFERINGS": "Framework + consulting for small agencies.",
        "ENGAGEMENT_MODEL": "Retainer + project-based.",
        "TOOL_STACK": "Hermes, SQLite, Git.",
        # Clients
        "ACTIVE_CLIENTS": "(currently none beyond myself)",
    }
    prompter = _scripted_prompter(answers)

    generated = run_tier3_interview(
        owner_name="Test Owner",
        org_name="Test Agency",
        cos_id=None,
        prompter=prompter,
        refresh=True,
    )

    assert GOALS_MD.exists()
    assert VALUES_MD.exists()
    assert PERSONAL_MD.exists()
    assert WORK_MD.exists()
    assert CLIENTS_MD.exists()

    # Spot-check substitutions actually landed
    goals = GOALS_MD.read_text(encoding="utf-8")
    assert "Help small agencies stop re-teaching their AI" in goals
    assert "Test Agency" in goals  # ORG_NAME substituted

    values = VALUES_MD.read_text(encoding="utf-8")
    assert "Truth over comfort" in values

    # Optional skipped questions leave placeholders intact
    personal = PERSONAL_MD.read_text(encoding="utf-8")
    assert "{{FAMILY_CONTEXT}}" in personal


@pytest.mark.seam
def test_state_files_initialized(tmp_agency):
    from _framework.ops.init.tier3_interview import run_tier3_interview
    from _framework.constants import OPERATIONAL_STATE_MD, CONVERSATION_JOURNAL_MD

    # Skip all answers — we just want the state-file initialization side
    answers = {}
    prompter = _scripted_prompter(answers)
    run_tier3_interview(
        owner_name="Solo Owner",
        org_name="Solo Inc",
        cos_id=None,
        prompter=prompter,
        refresh=True,
    )
    assert OPERATIONAL_STATE_MD.exists()
    assert CONVERSATION_JOURNAL_MD.exists()
    content = OPERATIONAL_STATE_MD.read_text(encoding="utf-8")
    assert "operational-state" in content.lower()
