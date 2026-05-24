# SEAM TEST — owned by HermesAgency.
"""
Weekly strategic-plan health check (v0.23.6).

Verifies the health-check module reads three-layer Goals.md +
metrics + firings + audit findings, and produces a structured
report that names drift + proposes pivots.
"""

from __future__ import annotations

import sys
import sqlite3
from datetime import datetime, timedelta, timezone
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


_SAMPLE_GOALS_MD = """# Goals

## The mission

Build technological intelligences that good ancestors would be proud of.

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

### Outcome 2 — Personal health

Weekly hours of focused exercise will increase from 1 hour in January 2026 to 4 hours by December 2027.

#### Interim Goals (layer 2) — leading indicators for Outcome 2

**Interim Goal 2.1 — Calendar protection**

The percentage of weeks where the Principal has 4+ protected exercise blocks will increase from 25% in January 2026 to 90% by December 2026.

Initiatives:
- script: `cos/exercise-block-protector.py` *(deterministic)*
"""


def _write_goals(tmp_path: Path, body: str = _SAMPLE_GOALS_MD) -> Path:
    p = tmp_path / "agency-vault" / "Goals.md"
    p.write_text(body, encoding="utf-8")
    return p


def _init_learning_db(tmp_path: Path) -> Path:
    """Create a minimal learning.db with the firings schema."""
    state_dir = tmp_path / "_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_dir / "learning.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE learning_rules (
            id TEXT PRIMARY KEY, correction TEXT, source TEXT,
            skill_tags TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, is_hard INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE firings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL,
            skill_tag TEXT NOT NULL,
            profile TEXT NOT NULL,
            was_overridden INTEGER NOT NULL DEFAULT 0,
            action_summary TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_path


def _record_firing(db_path: Path, skill_tag: str, when: datetime):
    """Insert a firing row tagged with skill_tag at the given time."""
    conn = sqlite3.connect(str(db_path))
    # Need a parent rule_id; insert a placeholder if missing
    conn.execute(
        "INSERT OR IGNORE INTO learning_rules (id, correction, source, "
        "skill_tags, created_at, updated_at) VALUES "
        "('lr_test', 'test', 'test', '[\"general\"]', ?, ?)",
        (when.isoformat(), when.isoformat()),
    )
    conn.execute(
        "INSERT INTO firings (rule_id, skill_tag, profile, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("lr_test", skill_tag, "devon", when.isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def test_health_check_returns_no_plan_when_goals_missing(tmp_path):
    from _framework.strategic_health import run_health_check
    report = run_health_check(include_audit=False)
    assert not report.has_strategic_plan
    assert report.outcomes == []


def test_health_check_returns_no_plan_for_legacy_flat_goals(tmp_path):
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path, "# Goals\n\n## The mission\n\nDo stuff.\n\n## Annual\n- thing\n")
    report = run_health_check(include_audit=False)
    assert not report.has_strategic_plan


def test_health_check_structures_three_layers_from_goals(tmp_path):
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    report = run_health_check(include_audit=False)
    assert report.has_strategic_plan
    assert len(report.outcomes) == 2
    o1 = report.outcomes[0]
    assert "Coaching" in o1.title
    assert len(o1.interim_goals) == 2
    assert o1.interim_goals[0].number == "1.1"
    # Initiatives are picked up from Goals.md
    assert len(o1.interim_goals[0].initiatives) == 2


def test_health_check_marks_initiatives_as_drift_when_no_firings(tmp_path):
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)  # DB exists but has no firings
    report = run_health_check(include_audit=False)
    o1_ig1 = report.outcomes[0].interim_goals[0]
    # Both Initiatives have zero firings → drift
    assert all(i.status == "drift" for i in o1_ig1.initiatives)
    # firings_30d should be 0
    assert all(i.firings_30d == 0 for i in o1_ig1.initiatives)


def test_health_check_marks_initiative_on_track_with_recent_firings(tmp_path):
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    db = _init_learning_db(tmp_path)
    now = datetime.now(timezone.utc)
    # Record 5 firings in the last 7 days, tagged by bare skill name
    for i in range(5):
        _record_firing(db, "lookalike-prospect-builder", now - timedelta(days=i))
    report = run_health_check(include_audit=False)
    o1_ig1 = report.outcomes[0].interim_goals[0]
    # The first initiative should be on-track now
    builder = next(
        (i for i in o1_ig1.initiatives
         if "lookalike-prospect-builder" in i.ref.path),
        None,
    )
    assert builder is not None
    assert builder.status == "on-track"
    assert builder.firings_30d == 5


def test_health_check_strips_py_suffix_for_script_firing_match(tmp_path):
    """Scripts often record firings tagged as `pipeline-watchdog`
    (no `.py`), even though Goals.md says `pipeline-watchdog.py`.
    The matcher tries both."""
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    db = _init_learning_db(tmp_path)
    now = datetime.now(timezone.utc)
    for i in range(3):
        _record_firing(db, "pipeline-watchdog", now - timedelta(days=i))
    report = run_health_check(include_audit=False)
    o1_ig1 = report.outcomes[0].interim_goals[0]
    watchdog = next(
        (i for i in o1_ig1.initiatives
         if "pipeline-watchdog" in i.ref.path),
        None,
    )
    assert watchdog is not None
    assert watchdog.firings_30d == 3
    assert watchdog.status == "on-track"


def test_health_check_proposes_pivots_for_drift(tmp_path):
    """When Initiatives have no firings, pivot proposals get generated."""
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)  # empty firings
    report = run_health_check(include_audit=False)
    assert report.pivot_proposals  # non-empty
    # At least one mentions an Initiative path
    joined = " | ".join(report.pivot_proposals)
    assert (
        "lookalike-prospect-builder" in joined
        or "pipeline-watchdog" in joined
        or "value-clarifier" in joined
        or "exercise-block-protector" in joined
    )


def test_health_check_caps_pivot_proposals_at_three(tmp_path):
    """The point is to focus the Principal on the most-pressing
    pivots, not list everything. Cap at 3."""
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    report = run_health_check(include_audit=False)
    assert len(report.pivot_proposals) <= 3


def test_health_check_metric_status_picked_up_by_ig_number(tmp_path):
    """If a metric named '1.1 Active engagements' is registered with
    no observations, IG 1.1 should report 'no-data' status (not missing)."""
    from _framework.strategic_health import run_health_check
    from _framework.goals.tracking import define_metric
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    # Register a metric tied to IG 1.1 via the name-prefix convention
    define_metric(
        goal_text="Active engagements",
        metric_name="1.1 active engagements count",
        measurement_type="counter",
        target_value=9.0,
    )
    report = run_health_check(include_audit=False)
    ig11 = report.outcomes[0].interim_goals[0]
    # The metric exists but has no observations
    assert ig11.metric_status in ("no-data", "at-risk")


def test_render_report_starts_with_pivots(tmp_path):
    """The rendered report should put pivot proposals FIRST — that's
    the point of the §7.4 cadence (pivots, not celebration)."""
    from _framework.strategic_health import run_health_check, render_report
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    report = run_health_check(include_audit=False)
    out = render_report(report)
    # The pivots heading should appear before the Outcomes heading
    pivot_pos = out.find("Pivots worth considering")
    outcomes_pos = out.find("## Outcomes")
    assert 0 <= pivot_pos < outcomes_pos


def test_render_report_handles_missing_plan(tmp_path):
    """If Goals.md isn't three-layer, the rendered report tells the
    Principal where to go (`/agency setup`)."""
    from _framework.strategic_health import run_health_check, render_report
    report = run_health_check(include_audit=False)
    out = render_report(report)
    assert "no strategic plan" in out.lower() or "setup" in out.lower()


def test_health_check_reads_only_never_mutates_vault(tmp_path):
    """v0.23.3 audit findings-only contract extends here: the health
    check reads vault files + DBs but never writes to the vault."""
    from _framework.strategic_health import run_health_check
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)

    vault = tmp_path / "agency-vault"
    before = {p.name: p.read_bytes() for p in vault.iterdir() if p.is_file()}
    run_health_check(include_audit=False)
    after = {p.name: p.read_bytes() for p in vault.iterdir() if p.is_file()}
    assert before == after


def test_agency_health_command_routes_to_health_check(tmp_path, monkeypatch):
    """`/agency health` runs the weekly health check and returns the
    rendered report. When no strategic plan exists, returns the
    setup-pointer message."""
    for mod in [m for m in list(sys.modules) if "hermes_agency_plugin" in m]:
        del sys.modules[mod]
    from hermes_agency_plugin.commands import handle_agency_command

    out = handle_agency_command("health")
    # No three-layer Goals.md in this fixture (Goals.md absent)
    assert out is not None
    assert (
        "no strategic plan" in out.lower()
        or "weekly strategic-plan health check" in out.lower()
    )
