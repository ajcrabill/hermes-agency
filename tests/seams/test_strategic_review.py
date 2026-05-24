# SEAM TEST — owned by HermesAgency.
"""
Quarterly strategic-review-prep (v0.23.7).

Verifies the prep module produces a structured packet covering the
three-layer plan summary, last-90-days activity, audit findings,
and the standard Principal-facing questions from
StrategicPlanning.md §6.3.
"""

from __future__ import annotations

import sys
import sqlite3
from datetime import date, datetime, timedelta, timezone
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
"""


def _write_goals(tmp_path: Path, body: str = _SAMPLE_GOALS_MD) -> Path:
    p = tmp_path / "agency-vault" / "Goals.md"
    p.write_text(body, encoding="utf-8")
    return p


def _init_learning_db(tmp_path: Path) -> Path:
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
    conn = sqlite3.connect(str(db_path))
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


# ── is_quarterly_trigger_day ────────────────────────────────────────────


def test_is_quarterly_trigger_day_jan_first_monday():
    from _framework.strategic_review import is_quarterly_trigger_day
    # First Monday of 2026 is Jan 5
    assert is_quarterly_trigger_day(date(2026, 1, 5))


def test_is_quarterly_trigger_day_apr_first_monday():
    from _framework.strategic_review import is_quarterly_trigger_day
    # First Monday of Apr 2026 is Apr 6
    assert is_quarterly_trigger_day(date(2026, 4, 6))


def test_is_quarterly_trigger_day_jul_first_monday():
    from _framework.strategic_review import is_quarterly_trigger_day
    # First Monday of Jul 2026 is Jul 6
    assert is_quarterly_trigger_day(date(2026, 7, 6))


def test_is_quarterly_trigger_day_oct_first_monday():
    from _framework.strategic_review import is_quarterly_trigger_day
    # First Monday of Oct 2026 is Oct 5
    assert is_quarterly_trigger_day(date(2026, 10, 5))


def test_is_quarterly_trigger_day_rejects_non_quarter_month():
    from _framework.strategic_review import is_quarterly_trigger_day
    # First Monday of Feb 2026 (Feb 2 — but Feb isn't a quarter)
    assert not is_quarterly_trigger_day(date(2026, 2, 2))


def test_is_quarterly_trigger_day_rejects_non_monday():
    from _framework.strategic_review import is_quarterly_trigger_day
    # Jan 6 2026 is a Tuesday
    assert not is_quarterly_trigger_day(date(2026, 1, 6))


def test_is_quarterly_trigger_day_rejects_later_monday_in_quarter_month():
    from _framework.strategic_review import is_quarterly_trigger_day
    # Jan 12 2026 is the second Monday — not first
    assert not is_quarterly_trigger_day(date(2026, 1, 12))


def test_next_quarterly_trigger_date_advances():
    from _framework.strategic_review import next_quarterly_trigger_date
    # From May 1, 2026 → next is first Monday of July 2026 (Jul 6)
    d = next_quarterly_trigger_date(after=date(2026, 5, 1))
    assert d.year == 2026 and d.month == 7
    # And the result itself is a trigger day
    from _framework.strategic_review import is_quarterly_trigger_day
    assert is_quarterly_trigger_day(d)


# ── produce_review_packet ───────────────────────────────────────────────


def test_packet_with_no_plan_notes_setup_needed(tmp_path):
    from _framework.strategic_review import produce_review_packet
    packet = produce_review_packet()
    assert not packet.has_strategic_plan
    # The packet still has a valid quarter label
    assert packet.quarter_label.startswith("Q")
    # Notes mention setup
    joined = " ".join(packet.notes).lower()
    assert "no three-layer" in joined or "setup" in joined


def test_packet_includes_three_layer_plan_summary(tmp_path):
    from _framework.strategic_review import produce_review_packet
    _write_goals(tmp_path)
    packet = produce_review_packet()
    assert packet.has_strategic_plan
    assert packet.mission
    assert "good ancestors" in packet.mission.lower()
    assert len(packet.plan_summary) == 1
    o = packet.plan_summary[0]
    assert o["number"] == 1
    assert "Coaching" in o["title"]
    assert len(o["interim_goals"]) == 1
    ig = o["interim_goals"][0]
    assert ig["number"] == "1.1"
    assert len(ig["initiatives"]) == 2


def test_packet_includes_firings_rollup(tmp_path):
    from _framework.strategic_review import produce_review_packet
    _write_goals(tmp_path)
    db = _init_learning_db(tmp_path)
    now = datetime.now(timezone.utc)
    # 7 firings of one skill, 3 of another, in last 90 days
    for i in range(7):
        _record_firing(db, "lookalike-prospect-builder", now - timedelta(days=i * 5))
    for i in range(3):
        _record_firing(db, "pipeline-watchdog", now - timedelta(days=i * 10))
    packet = produce_review_packet()
    assert packet.firings_total == 10
    assert packet.firings_by_tag.get("lookalike-prospect-builder") == 7
    assert packet.firings_by_tag.get("pipeline-watchdog") == 3


def test_packet_excludes_firings_older_than_period(tmp_path):
    from _framework.strategic_review import produce_review_packet
    _write_goals(tmp_path)
    db = _init_learning_db(tmp_path)
    old = datetime.now(timezone.utc) - timedelta(days=120)
    _record_firing(db, "lookalike-prospect-builder", old)
    packet = produce_review_packet(period_days=90)
    assert packet.firings_total == 0


def test_packet_quarterly_label_correct_for_q2(tmp_path):
    from _framework.strategic_review import produce_review_packet
    # Simulate generation in mid-Q2 2026 (May)
    packet = produce_review_packet(now=datetime(2026, 5, 15, tzinfo=timezone.utc))
    assert packet.quarter_label == "Q2 2026"


def test_packet_principal_questions_include_standard_set(tmp_path):
    from _framework.strategic_review import produce_review_packet
    _write_goals(tmp_path)
    packet = produce_review_packet()
    qs = " | ".join(packet.principal_questions).lower()
    assert "right outcomes" in qs
    assert "interim goal" in qs


def test_packet_adds_zero_firings_diagnostic_question(tmp_path):
    """If 0 firings recorded over the quarter, the packet flags this
    as a diagnostic question worth bringing to the meeting."""
    from _framework.strategic_review import produce_review_packet
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    packet = produce_review_packet()
    qs = " | ".join(packet.principal_questions).lower()
    assert "zero firings" in qs or "not being logged" in qs


# ── render_packet ───────────────────────────────────────────────────────


def test_render_packet_contains_all_four_sections(tmp_path):
    from _framework.strategic_review import (
        produce_review_packet, render_packet,
    )
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    rendered = render_packet(produce_review_packet())
    assert "The plan (current state)" in rendered
    assert "Activity (last 90 days)" in rendered
    assert "Audit signals" in rendered
    assert "Questions to bring to the review meeting" in rendered


def test_render_packet_no_plan_path(tmp_path):
    from _framework.strategic_review import (
        produce_review_packet, render_packet,
    )
    rendered = render_packet(produce_review_packet())
    assert "no strategic plan" in rendered.lower()
    assert "setup" in rendered.lower()


def test_packet_is_read_only_never_mutates_vault(tmp_path):
    """Quarterly-review prep follows v0.23.3 findings-only contract:
    reads the vault, never writes to it."""
    from _framework.strategic_review import produce_review_packet
    _write_goals(tmp_path)
    _init_learning_db(tmp_path)
    vault = tmp_path / "agency-vault"
    before = {p.name: p.read_bytes() for p in vault.iterdir() if p.is_file()}
    produce_review_packet()
    after = {p.name: p.read_bytes() for p in vault.iterdir() if p.is_file()}
    assert before == after


# ── /agency review-prep routing ─────────────────────────────────────────


def test_agency_review_prep_command_routes_to_prep(tmp_path, monkeypatch):
    """`/agency review-prep` invokes the quarterly packet skill."""
    for mod in [m for m in list(sys.modules) if "hermes_agency_plugin" in m]:
        del sys.modules[mod]
    from hermes_agency_plugin.commands import handle_agency_command

    out = handle_agency_command("review-prep")
    assert out is not None
    assert (
        "no strategic plan" in out.lower()
        or "quarterly strategic review" in out.lower()
    )


def test_agency_review_prep_underscore_alias(tmp_path, monkeypatch):
    """`review_prep` (underscore) is an alias for `review-prep`."""
    for mod in [m for m in list(sys.modules) if "hermes_agency_plugin" in m]:
        del sys.modules[mod]
    from hermes_agency_plugin.commands import handle_agency_command

    out = handle_agency_command("review_prep")
    assert out is not None
    assert (
        "no strategic plan" in out.lower()
        or "quarterly strategic review" in out.lower()
    )
