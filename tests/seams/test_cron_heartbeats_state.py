"""Tests for the small operational modules: cron sync, heartbeats, state files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Cron sync ───────────────────────────────────────────────────────────


def _make_profile_with_jobs(tmp_agency, profile_id: str, jobs: list[dict]) -> Path:
    prof = tmp_agency / "profiles" / profile_id
    (prof / "cron").mkdir(parents=True)
    (prof / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}, indent=2))
    return prof


@pytest.mark.seam
def test_cron_sync_adds_framework_jobs(tmp_agency, monkeypatch):
    hermes_home = tmp_agency.parent / ".hermes-cron-test"
    (hermes_home / "cron").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    _make_profile_with_jobs(tmp_agency, "cos", [
        {"name": "morning-briefing", "prompt": "...", "schedule": {"kind": "cron", "expr": "0 6 * * *"}},
        {"name": "weekly-review",     "prompt": "...", "schedule": {"kind": "cron", "expr": "0 7 * * 0"}},
    ])
    _make_profile_with_jobs(tmp_agency, "sentinel", [
        {"name": "learning-monitor", "prompt": "...", "schedule": {"kind": "interval", "minutes": 5}},
    ])

    from _framework.cron import sync_cron_jobs

    summary = sync_cron_jobs()
    assert summary["framework_jobs_after"] == 3
    assert summary["operator_jobs"] == 0

    target_doc = json.loads((hermes_home / "cron" / "jobs.json").read_text())
    assert len(target_doc["jobs"]) == 3
    assert all(j["origin"] == "hermes-agency" for j in target_doc["jobs"])
    assert all("hermes_agency_key" in j for j in target_doc["jobs"])


@pytest.mark.seam
def test_cron_sync_preserves_operator_jobs(tmp_agency, monkeypatch):
    hermes_home = tmp_agency.parent / ".hermes-cron-op"
    (hermes_home / "cron").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    # Pre-existing operator job (no origin field)
    (hermes_home / "cron" / "jobs.json").write_text(json.dumps({
        "jobs": [
            {"id": "op1", "name": "operator-job", "prompt": "manual"},
        ]
    }))

    _make_profile_with_jobs(tmp_agency, "cos", [
        {"name": "morning-briefing", "prompt": "...", "schedule": {"kind": "cron", "expr": "0 6 * * *"}},
    ])

    from _framework.cron import sync_cron_jobs

    summary = sync_cron_jobs()
    assert summary["operator_jobs"] == 1
    assert summary["framework_jobs_after"] == 1

    target_doc = json.loads((hermes_home / "cron" / "jobs.json").read_text())
    names = [j["name"] for j in target_doc["jobs"]]
    assert "operator-job" in names
    assert "morning-briefing" in names


@pytest.mark.seam
def test_cron_sync_replaces_framework_jobs_cleanly(tmp_agency, monkeypatch):
    """Second sync replaces our jobs in place — no duplicates."""
    hermes_home = tmp_agency.parent / ".hermes-cron-replace"
    (hermes_home / "cron").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    _make_profile_with_jobs(tmp_agency, "cos", [
        {"name": "morning-briefing", "prompt": "...", "schedule": {"kind": "cron", "expr": "0 6 * * *"}},
    ])

    from _framework.cron import sync_cron_jobs
    sync_cron_jobs()
    sync_cron_jobs()
    target_doc = json.loads((hermes_home / "cron" / "jobs.json").read_text())
    framework_jobs = [j for j in target_doc["jobs"] if j["origin"] == "hermes-agency"]
    assert len(framework_jobs) == 1   # no duplication


# ── Heartbeats ──────────────────────────────────────────────────────────


@pytest.mark.seam
def test_heartbeat_records_and_last_beat(tmp_agency):
    from _framework.heartbeats import beat, last_beat, recent
    beat("morning-briefing")
    assert last_beat("morning-briefing") is not None
    rows = recent("morning-briefing")
    assert len(rows) == 1


@pytest.mark.seam
def test_heartbeat_with_payload(tmp_agency):
    from _framework.heartbeats import beat_with_payload, recent
    beat_with_payload("email-triage", {"items_processed": 12, "errors": 0})
    rows = recent("email-triage")
    assert rows[0]["payload"]
    assert "items_processed" in rows[0]["payload"]


@pytest.mark.seam
def test_stale_components_uses_expected_intervals(tmp_agency):
    """A component with no recent beat is reported stale."""
    from _framework.heartbeats import beat, stale_components
    from _framework.heartbeats.heartbeats import _conn
    import time
    from datetime import datetime, timedelta, timezone

    beat("learning-monitor")
    # Force the last_success_at backwards to simulate stale
    db = _conn()
    try:
        long_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        db.execute("UPDATE heartbeat_summary SET last_success_at=? WHERE component=?",
                   (long_ago, "learning-monitor"))
        db.commit()
    finally:
        db.close()
    stale = stale_components()
    assert any(s["component"] == "learning-monitor" for s in stale)


# ── State files ─────────────────────────────────────────────────────────


@pytest.mark.seam
def test_append_to_section_creates_section(tmp_agency):
    from _framework.state import append_to_section
    from _framework.constants import OPERATIONAL_STATE_MD

    append_to_section(OPERATIONAL_STATE_MD, "New section", "First entry here.")
    text = OPERATIONAL_STATE_MD.read_text()
    assert "## New section" in text
    assert "First entry here" in text


@pytest.mark.seam
def test_append_to_existing_section(tmp_agency):
    from _framework.state import append_to_section
    from _framework.constants import OPERATIONAL_STATE_MD

    OPERATIONAL_STATE_MD.parent.mkdir(parents=True, exist_ok=True)
    OPERATIONAL_STATE_MD.write_text(
        "# operational-state\n\n## Known issues\n\n(none yet)\n\n## Active delegations\n\n(none yet)\n"
    )
    append_to_section(OPERATIONAL_STATE_MD, "Known issues", "Bug found in X.")
    text = OPERATIONAL_STATE_MD.read_text()
    assert "Bug found in X" in text
    # Should not have created a duplicate section
    assert text.count("## Known issues") == 1
    # Entry should be in Known issues, before Active delegations
    assert text.index("Bug found in X") < text.index("## Active delegations")
