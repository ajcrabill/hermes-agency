# SEAM TEST — owned by HermesAgency.
"""
Three-layer Goals.md parser (v0.23.4).

Verifies the strategic-structure parser handles real templates +
hand-edited variations, and that the audit can cross-reference
skill frontmatter to the structure parsed here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_agency_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_AGENCY_STATE", str(tmp_path / "_state"))
    (tmp_path / "agency-vault").mkdir(parents=True, exist_ok=True)
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]
    yield
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]


_SAMPLE_GOALS_MD = """# Goals — Good Ancestor

_Strategic plan, layer 1 (Outcomes) + layer 2 (Interim Goals)._

---

## The mission

To build technological intelligences that good ancestors would be proud of.

---

## Outcomes (layer 1) — what success looks like

### Outcome 1 — Coaching practice revenue

Annual revenue from one-on-one coaching engagements will increase from $180k in January 2025 to $300k by December 2027.

#### Interim Goals (layer 2) — leading indicators for Outcome 1

**Interim Goal 1.1 — Active engagements**

The number of active monthly coaching engagements will increase from 5 in January 2026 to 9 by December 2026.

Initiatives (skills + scripts) serving Interim Goal 1.1:
- skill: `devon/lookalike-prospect-builder` *(agentic)*
- script: `devon/pipeline-watchdog.py` *(deterministic)*

**Interim Goal 1.2 — Engagement value**

The average revenue per coaching engagement will increase from $3,000 per month in January 2026 to $3,500 per month by December 2026.

Initiatives:
- skill: `devon/value-clarifier`

### Outcome 2 — Personal health (the non-business Outcome)

Weekly hours of focused exercise will increase from 1 hour in January 2026 to 4 hours by December 2027.

#### Interim Goals (layer 2) — leading indicators for Outcome 2

**Interim Goal 2.1 — Calendar protection for exercise blocks**

The percentage of weeks where the Principal has 4+ protected exercise blocks will increase from 25% in January 2026 to 90% by December 2026.

Initiatives:
- script: `cos/exercise-block-protector.py` *(deterministic)*
- skill: `cos/weekly-exercise-checkin` *(agentic)*

---
"""


def _write_goals(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "agency-vault" / "Goals.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_read_goals_strategic_returns_none_when_no_file():
    from _framework.goals import read_goals_strategic
    assert read_goals_strategic() is None


def test_read_goals_strategic_returns_none_for_legacy_flat_format(tmp_path):
    """Legacy Goals.md (no `## Outcomes` section) returns None;
    callers fall back to the flat `read_goals()` API."""
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, """# Goals — Org

## The mission

Build a thing.

## The current year's goals

- Ship v0.1 by March
  - Interim: prototype by Jan
""")
    assert read_goals_strategic() is None


def test_read_goals_strategic_extracts_outcomes(tmp_path):
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, _SAMPLE_GOALS_MD)
    parsed = read_goals_strategic()
    assert parsed is not None
    assert len(parsed.outcomes) == 2
    assert parsed.outcomes[0].number == 1
    assert "Coaching practice revenue" in parsed.outcomes[0].title
    assert "$180k" in parsed.outcomes[0].statement
    assert parsed.outcomes[1].number == 2
    assert "Personal health" in parsed.outcomes[1].title


def test_read_goals_strategic_extracts_interim_goals(tmp_path):
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, _SAMPLE_GOALS_MD)
    parsed = read_goals_strategic()
    o1 = parsed.outcomes[0]
    assert len(o1.interim_goals) == 2
    assert o1.interim_goals[0].number == "1.1"
    assert "Active engagements" in o1.interim_goals[0].title
    assert "5 in January 2026" in o1.interim_goals[0].statement
    assert o1.interim_goals[1].number == "1.2"
    o2 = parsed.outcomes[1]
    assert len(o2.interim_goals) == 1


def test_read_goals_strategic_extracts_initiative_refs(tmp_path):
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, _SAMPLE_GOALS_MD)
    parsed = read_goals_strategic()
    refs_1_1 = parsed.outcomes[0].interim_goals[0].initiative_refs
    assert len(refs_1_1) == 2
    kinds = {r.kind for r in refs_1_1}
    paths = {r.path for r in refs_1_1}
    assert kinds == {"skill", "script"}
    assert "devon/lookalike-prospect-builder" in paths
    assert "devon/pipeline-watchdog.py" in paths


def test_strategic_goals_aggregation_helpers(tmp_path):
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, _SAMPLE_GOALS_MD)
    parsed = read_goals_strategic()
    interim_keys = parsed.all_interim_goal_keys()
    assert set(interim_keys) == {"1.1", "1.2", "2.1"}
    outcome_keys = parsed.all_outcome_numbers()
    assert outcome_keys == ["O1", "O2"]
    all_refs = parsed.all_initiative_refs()
    paths = {r.path for r in all_refs}
    assert "devon/lookalike-prospect-builder" in paths
    assert "cos/exercise-block-protector.py" in paths


def test_read_goals_strategic_handles_template_with_placeholders(tmp_path):
    """The unrendered template (with {{...}} placeholders) shouldn't
    crash; statements that are pure placeholders are left empty."""
    from _framework.goals import read_goals_strategic
    template = """# Goals — {{ORG_NAME}}

## Outcomes (layer 1) — what success looks like

### Outcome 1 — {{OUTCOME_1_TITLE}}

{{OUTCOME_1_STATEMENT}}

#### Interim Goals (layer 2) — leading indicators for Outcome 1

**Interim Goal 1.1 — {{INTERIM_1_1_TITLE}}**

{{INTERIM_1_1_STATEMENT}}

Initiatives (skills + scripts) serving Interim Goal 1.1:
- skill: `{{PROFILE_1_1_A}}/{{SKILL_1_1_A}}` *(agentic)*
"""
    _write_goals(tmp_path, template)
    parsed = read_goals_strategic()
    assert parsed is not None
    assert len(parsed.outcomes) == 1
    # Title still parses (template substitution markers are part of
    # the visible text)
    assert "{{OUTCOME_1_TITLE}}" in parsed.outcomes[0].title


def test_read_goals_strategic_extracts_mission(tmp_path):
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, _SAMPLE_GOALS_MD)
    parsed = read_goals_strategic()
    assert "good ancestors" in parsed.mission.lower()


def test_read_goals_strategic_empty_when_no_outcomes_section(tmp_path):
    """File with `# Goals` but no `## Outcomes` → returns None
    (treated as legacy / unconfigured)."""
    from _framework.goals import read_goals_strategic
    _write_goals(tmp_path, "# Goals\n\nThis isn't the strategic format.")
    assert read_goals_strategic() is None
