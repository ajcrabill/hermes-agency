"""Goals module tests — SMART checker + Goals.md round-trip."""

from __future__ import annotations

import pytest


# ── SMART checker ──────────────────────────────────────────────────────


@pytest.mark.seam
def test_smart_vague_goal_fails_most_dimensions(tmp_agency):
    from _framework.goals import smart_check
    v = smart_check("Grow the business.")
    assert v.specific is False or v.measurable is False
    assert v.time_bound is False
    assert v.missing


@pytest.mark.seam
def test_smart_clear_goal_passes(tmp_agency):
    from _framework.goals import smart_check
    v = smart_check(
        "Sign 4 new district clients by end of Q3 in service of the "
        "agency's mission to scale governance coaching."
    )
    assert v.specific is True
    assert v.measurable is True   # "4 new" + "sign"
    assert v.time_bound is True   # "end of Q3"
    assert v.relevant is True     # "in service of"
    assert v.is_smart


@pytest.mark.seam
def test_smart_binary_outcome_recognized(tmp_agency):
    from _framework.goals import smart_check
    v = smart_check("Ship the K-12 governance playbook by November 2026.")
    assert v.measurable is True   # binary "ship"
    assert v.time_bound is True   # "by November 2026"


@pytest.mark.seam
def test_smart_missing_time_surfaces_question(tmp_agency):
    from _framework.goals import smart_check
    v = smart_check("Sign 4 new district clients in service of the mission.")
    assert v.time_bound is False
    assert any("when" in q.lower() for q in v.missing)


# ── Goals.md round-trip ─────────────────────────────────────────────────


def _seed_goals_md(tmp_agency, content: str):
    from _framework.constants import GOALS_MD, AGENCY_VAULT
    AGENCY_VAULT.mkdir(parents=True, exist_ok=True)
    GOALS_MD.write_text(content, encoding="utf-8")


@pytest.mark.seam
def test_read_empty_goals_returns_empty_parsed(tmp_agency):
    from _framework.goals import read_goals
    parsed = read_goals()
    assert parsed.annual_goals == []


@pytest.mark.seam
def test_read_goals_parses_sections(tmp_agency):
    _seed_goals_md(tmp_agency, """# Goals — Test Org

## The mission

Help small agencies stop re-teaching their AI.

## The current year's goals

- Sign 4 district clients by Q3.
  - Q1: ship the pitch deck
  - Q2: 8 qualified conversations
- Publish the governance playbook by November.

## Active strategic projects

- **HermesAgency v1.0** — framework GA release.

## What we're NOT working on

- Building yet another single-agent assistant.
""")
    from _framework.goals import read_goals
    parsed = read_goals()
    assert "Help small agencies" in parsed.section("The mission")
    assert len(parsed.annual_goals) == 2
    assert parsed.annual_goals[0].text.startswith("Sign 4 district clients")
    assert len(parsed.annual_goals[0].interim) == 2
    assert parsed.annual_goals[0].interim[0].startswith("Q1: ship")


@pytest.mark.seam
def test_add_annual_goal_appends_with_interim(tmp_agency):
    _seed_goals_md(tmp_agency, """# Goals — Test Org

## The mission

Mission text.

## The current year's goals

- Existing goal one.
  - Existing milestone.

## Active strategic projects

(none)
""")
    from _framework.goals import add_annual_goal, read_goals

    add_annual_goal(
        "Sign 4 new district clients by end of Q3.",
        interim=["Q1: ship the pitch deck",
                 "Q2: 8 qualified conversations",
                 "Q3: signed 4 clients"],
    )
    parsed = read_goals()
    assert len(parsed.annual_goals) == 2
    new_goal = parsed.annual_goals[-1]
    assert "Sign 4 new district clients" in new_goal.text
    assert len(new_goal.interim) == 3


@pytest.mark.seam
def test_replace_annual_goal(tmp_agency):
    _seed_goals_md(tmp_agency, """# Goals — Test Org

## The current year's goals

- Vague goal.
  - Vague milestone.
- Another goal.
""")
    from _framework.goals import replace_annual_goal, read_goals
    replace_annual_goal(
        0,
        "Sharp specific measurable goal by Q4.",
        interim=["Q1: foundation", "Q2: build", "Q3: ship"],
    )
    parsed = read_goals()
    assert "Sharp specific measurable" in parsed.annual_goals[0].text
    assert "Another goal" in parsed.annual_goals[1].text   # untouched


@pytest.mark.seam
def test_replace_annual_goal_index_out_of_range(tmp_agency):
    _seed_goals_md(tmp_agency, """# Goals

## The current year's goals

- One.
""")
    from _framework.goals import replace_annual_goal
    with pytest.raises(IndexError):
        replace_annual_goal(5, "anything")


@pytest.mark.seam
def test_write_back_preserves_other_sections(tmp_agency):
    _seed_goals_md(tmp_agency, """# Goals — Test Org

## The mission

The mission as written by the operator.

## The current year's goals

- First goal.

## What we're NOT working on

- Not doing X.
- Not doing Y.

## Decision principles when goals conflict

When in doubt, family first.
""")
    from _framework.goals import add_annual_goal, read_goals
    add_annual_goal("Second goal by Q4.")
    parsed = read_goals()
    # The other sections should still be present
    assert "The mission as written by the operator" in parsed.section("The mission")
    assert "Not doing X" in parsed.section("What we're NOT working on")
    assert "family first" in parsed.section("Decision principles when goals conflict")
