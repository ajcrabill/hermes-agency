"""Agent personalization tests — per-agent name/pronouns/personality."""

from __future__ import annotations

import pytest


def _scripted(answers: dict[str, str]):
    """Map fragment-of-question → answer."""
    def _p(question: str, default: str, hint: str) -> str:
        for k, v in answers.items():
            if k.lower() in question.lower():
                return v if v != "" else default
        return default
    return _p


@pytest.mark.seam
def test_personalize_returns_personas(tmp_agency):
    from _framework.ops.init.agent_personalization import personalize_agents

    prompter = _scripted({
        "Display name": "Maya",
        "Pronouns": "she",
        "Personality": "Warm, methodical, and direct when asked. Never effusive.",
    })
    personas = personalize_agents(
        profiles=[("cos", "chief-of-staff")],
        prompter=prompter,
    )
    assert len(personas) == 1
    p = personas[0]
    assert p.profile_id == "cos"
    assert p.display_name == "Maya"
    assert p.pronouns == "she/her"
    assert "Warm" in p.personality_notes


@pytest.mark.seam
def test_pronoun_options_handled(tmp_agency):
    from _framework.ops.init.agent_personalization import personalize_agents

    cases = [
        ("she", "she/her"),
        ("he",  "he/him"),
        ("they", "they/them"),
        ("it",  "it/its"),
        ("none", ""),    # unrecognized → falls through to no pronouns
        ("",    ""),
    ]
    for raw, expected in cases:
        prompter = _scripted({"Pronouns": raw, "Display name": "X", "Personality": ""})
        personas = personalize_agents(profiles=[("cos", "chief-of-staff")], prompter=prompter)
        assert personas[0].pronouns == expected, f"for input {raw!r}"


@pytest.mark.seam
def test_appendix_writes_to_soul(tmp_agency):
    from _framework.ops.init.agent_personalization import (
        AgentPersona, write_persona_appendices,
    )
    from _framework.constants import profile_soul
    from _framework.scaffolds import scaffold_profile

    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "Test", "OWNER_NAME": "Test", "COS_EMAIL": "x@example.com",
    })

    persona = AgentPersona(
        profile_id="cos", role="chief-of-staff",
        display_name="Maya", pronouns="she/her",
        personality_notes="Calm and methodical.",
    )
    written = write_persona_appendices([persona], interview_date="2026-05-24")
    assert "cos" in written

    text = profile_soul("cos").read_text(encoding="utf-8")
    assert "## Personalization" in text
    assert "Display name:** Maya" in text
    assert "Pronouns:** she/her" in text
    assert "Calm and methodical" in text


@pytest.mark.seam
def test_appendix_skips_when_all_default(tmp_agency):
    from _framework.ops.init.agent_personalization import (
        AgentPersona, write_persona_appendices,
    )
    from _framework.scaffolds import scaffold_profile

    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "T", "OWNER_NAME": "T", "COS_EMAIL": "x@example.com",
    })

    persona = AgentPersona(
        profile_id="cos", role="chief-of-staff",
        display_name="cos",     # same as profile_id
        pronouns="",
        personality_notes="",
    )
    written = write_persona_appendices([persona], interview_date="2026-05-24")
    assert written == []   # nothing meaningful captured — skip silently


@pytest.mark.seam
def test_tier3_with_personalization_integration(tmp_agency):
    """Full Tier 3 + personalization path."""
    from _framework.ops.init.tier3_interview import run_tier3_interview
    from _framework.constants import profile_soul
    from _framework.scaffolds import scaffold_profile

    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "T", "OWNER_NAME": "T", "COS_EMAIL": "x@example.com",
    })

    answers_main = {
        "MISSION_STATEMENT": "Mission",
        "ANNUAL_GOALS": "Goal",
        "CORE_VALUES": "Truth.",
    }
    def main_prompter(q):
        return answers_main.get(q.key, "skip" if q.optional else "")

    persona_prompter = _scripted({
        "Display name": "Maya",
        "Pronouns": "they",
        "Personality": "Even-keeled, dry humor, calls things by their right name.",
    })

    run_tier3_interview(
        owner_name="Test Owner", org_name="Test Agency", cos_id="cos",
        prompter=main_prompter,
        persona_prompter=persona_prompter,
        profiles_to_personalize=[("cos", "chief-of-staff")],
        refresh=True,
    )
    text = profile_soul("cos").read_text(encoding="utf-8")
    assert "Maya" in text
    assert "they/them" in text
    assert "Even-keeled" in text
