"""Goal tracking tests — metrics, observations, status, milestones."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.seam
def test_define_metric_then_list(tmp_agency):
    from _framework.goals import define_metric, list_metrics
    mid = define_metric(
        goal_text="Sign 4 new district clients by end of Q3.",
        metric_name="signed_clients",
        measurement_type="counter",
        unit="clients",
        target_value=4,
        target_at="2026-09-30",
        data_source="crm.leads WHERE status='converted'",
    )
    assert mid > 0
    metrics = list_metrics()
    assert len(metrics) == 1
    assert metrics[0].metric_name == "signed_clients"
    assert metrics[0].target_value == 4


@pytest.mark.seam
def test_define_metric_is_idempotent(tmp_agency):
    """Re-defining the same (goal, metric_name) updates rather than duplicates."""
    from _framework.goals import define_metric, list_metrics
    define_metric(
        goal_text="Goal A", metric_name="m1",
        measurement_type="counter", target_value=10,
    )
    define_metric(
        goal_text="Goal A", metric_name="m1",
        measurement_type="counter", target_value=20,    # updated target
    )
    metrics = list_metrics()
    assert len(metrics) == 1
    assert metrics[0].target_value == 20


@pytest.mark.seam
def test_record_observations_and_latest(tmp_agency):
    from _framework.goals import (
        define_metric, record_observation, latest_observation,
    )
    mid = define_metric(
        goal_text="Goal", metric_name="m",
        measurement_type="gauge", target_value=100,
    )
    record_observation(metric_id=mid, value=10)
    record_observation(metric_id=mid, value=25)
    latest = latest_observation(mid)
    assert latest["value"] == 25


@pytest.mark.seam
def test_metric_status_on_track(tmp_agency):
    """Metric created today, with 50% of the time window elapsed and
    50%+ of the target achieved → on-track."""
    from _framework.goals import (
        define_metric, record_observation, metric_status,
    )
    from _framework.goals.tracking import _conn
    # Create a metric with target 10 weeks from now, and a target_value of 10
    now = datetime.now(timezone.utc)
    target_at = (now + timedelta(weeks=10)).isoformat()
    mid = define_metric(
        goal_text="Goal", metric_name="m",
        measurement_type="counter", target_value=10, target_at=target_at,
    )
    # Backdate created_at to 5 weeks ago (50% elapsed)
    five_weeks_ago = (now - timedelta(weeks=5)).isoformat()
    db = _conn()
    db.execute("UPDATE goal_metrics SET created_at=? WHERE id=?",
               (five_weeks_ago, mid))
    db.commit()
    db.close()
    # Observe 6/10 (60%, above the 50% pace)
    record_observation(metric_id=mid, value=6)
    status = metric_status(mid)
    assert status["status"] == "on-track"


@pytest.mark.seam
def test_metric_status_at_risk(tmp_agency):
    """50% time elapsed but only 20% achieved → at-risk."""
    from _framework.goals import (
        define_metric, record_observation, metric_status,
    )
    from _framework.goals.tracking import _conn
    now = datetime.now(timezone.utc)
    target_at = (now + timedelta(weeks=10)).isoformat()
    mid = define_metric(
        goal_text="Goal", metric_name="m",
        measurement_type="counter", target_value=10, target_at=target_at,
    )
    five_weeks_ago = (now - timedelta(weeks=5)).isoformat()
    db = _conn()
    db.execute("UPDATE goal_metrics SET created_at=? WHERE id=?",
               (five_weeks_ago, mid))
    db.commit()
    db.close()
    record_observation(metric_id=mid, value=2)   # 20% of target, well below 50% pace
    status = metric_status(mid)
    assert status["status"] == "at-risk"


@pytest.mark.seam
def test_metric_status_missed(tmp_agency):
    """Deadline passed without reaching target → missed."""
    from _framework.goals import (
        define_metric, record_observation, metric_status,
    )
    now = datetime.now(timezone.utc)
    target_at = (now - timedelta(weeks=2)).isoformat()   # 2 weeks ago
    mid = define_metric(
        goal_text="Goal", metric_name="m",
        measurement_type="counter", target_value=10, target_at=target_at,
    )
    record_observation(metric_id=mid, value=5)   # only 50% of target
    status = metric_status(mid)
    assert status["status"] == "missed"


@pytest.mark.seam
def test_metric_status_done_after_deadline(tmp_agency):
    """Target reached, deadline passed → done."""
    from _framework.goals import (
        define_metric, record_observation, metric_status,
    )
    now = datetime.now(timezone.utc)
    target_at = (now - timedelta(weeks=2)).isoformat()
    mid = define_metric(
        goal_text="Goal", metric_name="m",
        measurement_type="counter", target_value=10, target_at=target_at,
    )
    record_observation(metric_id=mid, value=12)
    status = metric_status(mid)
    assert status["status"] == "done"


@pytest.mark.seam
def test_metric_status_no_data(tmp_agency):
    """Metric defined but no observations → no-data."""
    from _framework.goals import define_metric, metric_status
    mid = define_metric(
        goal_text="Goal", metric_name="m",
        measurement_type="counter", target_value=5, target_at="2026-12-31",
    )
    status = metric_status(mid)
    assert status["status"] == "no-data"


@pytest.mark.seam
def test_weekly_status_report_aggregate(tmp_agency):
    from _framework.goals import (
        define_metric, record_observation, weekly_status_report,
    )
    define_metric(
        goal_text="G1", metric_name="m1",
        measurement_type="counter", target_value=10, target_at="2026-12-31",
    )
    define_metric(
        goal_text="G2", metric_name="m2",
        measurement_type="counter", target_value=5, target_at="2026-12-31",
    )
    report = weekly_status_report()
    assert report["total_metrics"] == 2
    assert report["no_data"] == 2


@pytest.mark.seam
def test_sync_milestones_from_goals_md(tmp_agency):
    from _framework.goals import sync_milestones_from_goals_md, list_milestones
    from _framework.constants import GOALS_MD, AGENCY_VAULT
    AGENCY_VAULT.mkdir(parents=True, exist_ok=True)
    GOALS_MD.write_text(
        "# Goals — Test\n\n"
        "## The current year's goals\n\n"
        "- Sign 4 new district clients by Q3.\n"
        "  - Q1: ship the pitch deck\n"
        "  - Q2: 8 qualified conversations\n"
        "  - Q3: 4 signed clients\n"
        "- Ship the playbook by November 2026.\n"
    )
    n = sync_milestones_from_goals_md()
    assert n == 3   # three sub-bullets on goal 1; none on goal 2
    milestones = list_milestones()
    assert len(milestones) == 3
    # Date hint extraction: Q1 → 03-31 of current year
    q1 = next(m for m in milestones if m["milestone_text"].startswith("Q1"))
    assert q1["target_at"] is not None
    assert "-03-31" in q1["target_at"]


@pytest.mark.seam
def test_extract_date_hint_variations(tmp_agency):
    from _framework.goals.tracking import _extract_date_hint
    assert "-09-30" in (_extract_date_hint("Sign 4 clients by Q3") or "")
    assert "2026-11-30" == _extract_date_hint("Ship the playbook by November 2026")
    assert "2026-12-15" == _extract_date_hint("Deadline 2026-12-15 for the doc")
    assert _extract_date_hint("vague target someday") is None


@pytest.mark.seam
def test_mark_milestone_done(tmp_agency):
    from _framework.goals import upsert_milestone, mark_milestone, list_milestones
    mid = upsert_milestone(
        goal_text="Goal", milestone_text="Ship the thing", target_at="2026-09-30",
    )
    mark_milestone(mid, status="done", completed_at="2026-09-15T12:00:00+00:00")
    done = list_milestones(status="done")
    assert len(done) == 1
    assert done[0]["completed_at"] == "2026-09-15T12:00:00+00:00"
