# SEAM TEST — owned by HermesAgency.
"""
SKILL.md frontmatter parser + script metadata extractor (v0.23.2).

Verifies the v0.23 Thread B requirement: strategic-alignment keys
in SKILL.md / script docstring are parseable, with `interim_goal`
gating whether a skill counts as part of the strategic plan.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_agency_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_AGENCY_STATE", str(tmp_path / "_state"))
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]
    yield
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_skill_frontmatter_returns_empty_when_no_file():
    from _framework.skills_meta import parse_skill_frontmatter
    assert parse_skill_frontmatter("/nonexistent/path.md") == {}


def test_parse_skill_frontmatter_returns_empty_when_no_frontmatter(tmp_path):
    from _framework.skills_meta import parse_skill_frontmatter
    p = _write(tmp_path, "skill.md", "# Just a heading, no frontmatter.\n")
    assert parse_skill_frontmatter(p) == {}


def test_parse_skill_frontmatter_extracts_basic_keys(tmp_path):
    from _framework.skills_meta import parse_skill_frontmatter
    p = _write(tmp_path, "skill.md", """---
skill_id: weekly-review
profile: loriah
role: chief-of-staff
---

# Weekly review
Body text.
""")
    fm = parse_skill_frontmatter(p)
    assert fm["skill_id"] == "weekly-review"
    assert fm["profile"] == "loriah"
    assert fm["role"] == "chief-of-staff"


def test_parse_skill_frontmatter_extracts_strategic_alignment_keys(tmp_path):
    from _framework.skills_meta import parse_skill_frontmatter
    p = _write(tmp_path, "skill.md", """---
skill_id: lookalike-prospect-builder
profile: devon
outcome: O1
interim_goal: G1.1
outcome_metric: "Look-alike prospects will increase from 0 in Feb 2026 to 50 by Apr 2026"
status: green
alignment_argument: "Look-alike prospects historically convert at 3x base rate"
owner_profile: devon
---

# Body
""")
    fm = parse_skill_frontmatter(p)
    assert fm["outcome"] == "O1"
    assert fm["interim_goal"] == "G1.1"
    assert "Look-alike prospects" in fm["outcome_metric"]
    assert fm["status"] == "green"
    assert fm["alignment_argument"].startswith("Look-alike prospects historically")
    assert fm["owner_profile"] == "devon"


def test_parse_skill_frontmatter_inline_list(tmp_path):
    from _framework.skills_meta import parse_skill_frontmatter
    p = _write(tmp_path, "skill.md", """---
voice_tags: [direct, we-not-i]
---
""")
    assert parse_skill_frontmatter(p)["voice_tags"] == ["direct", "we-not-i"]


def test_parse_skill_frontmatter_block_list(tmp_path):
    from _framework.skills_meta import parse_skill_frontmatter
    p = _write(tmp_path, "skill.md", """---
output_metrics:
  - blockers_surfaced_per_week
  - principal_decisions_per_week
---
""")
    metrics = parse_skill_frontmatter(p)["output_metrics"]
    assert metrics == ["blockers_surfaced_per_week", "principal_decisions_per_week"]


def test_is_strategic_skill_gates_on_interim_goal(tmp_path):
    from _framework.skills_meta import is_strategic_skill
    strategic = _write(tmp_path, "s.md", """---
skill_id: s
interim_goal: G1.1
---
""")
    utility = _write(tmp_path, "u.md", """---
skill_id: u
---
""")
    assert is_strategic_skill(strategic) is True
    assert is_strategic_skill(utility) is False


def test_parse_script_metadata_extracts_meta_block(tmp_path):
    from _framework.skills_meta import parse_script_metadata
    p = _write(tmp_path, "script.py", '''
"""Pipeline watchdog."""

# --- HERMES_AGENCY_META_START
# outcome: O1
# interim_goal: G1.2
# outcome_metric: "Nudge rate from 20% in Mar 2026 to 90% by Jun 2026"
# status: yellow
# owner_profile: devon
# --- HERMES_AGENCY_META_END

import sys
print("real code")
''')
    meta = parse_script_metadata(p)
    assert meta["outcome"] == "O1"
    assert meta["interim_goal"] == "G1.2"
    assert meta["status"] == "yellow"
    assert "Nudge rate" in meta["outcome_metric"]


def test_parse_script_metadata_empty_when_no_block(tmp_path):
    from _framework.skills_meta import parse_script_metadata
    p = _write(tmp_path, "script.py", '"""Just a script."""\nprint("hi")\n')
    assert parse_script_metadata(p) == {}


def test_strategic_frontmatter_keys_constant():
    """The public list of strategic keys must match the spec."""
    from _framework.skills_meta import STRATEGIC_FRONTMATTER_KEYS
    expected = {
        "outcome",
        "interim_goal",
        "outcome_metric",
        "status",
        "alignment_argument",
        "output_metrics",
        "input_metrics",
        "owner_profile",
    }
    assert set(STRATEGIC_FRONTMATTER_KEYS) == expected
