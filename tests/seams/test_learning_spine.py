"""
Learning subsystem — end-to-end spine tests.

Exercises the seven-step learning loop in narrow, fast unit shapes:

  CAPTURE  → tag → inject → record → recapture

These tests run against an isolated temp database (via the `tmp_agency`
fixture in conftest.py) — they never touch the real $AGENCY_HOME.
"""

from __future__ import annotations

import time

import pytest


@pytest.mark.seam
def test_schema_creates_idempotently(tmp_agency):
    from _framework.learning.learning_db import init_learning_db, get_db
    p = init_learning_db()
    assert p.exists()
    init_learning_db()  # idempotent
    db = get_db()
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    db.close()
    names = {r["name"] for r in rows}
    for required in ("meta", "learning_rules", "firings", "recapture_events", "recapture_denylist"):
        assert required in names


@pytest.mark.seam
def test_capture_persists_rule(tmp_agency):
    from _framework.learning import capture_correction
    from _framework.learning.learning_db import get_db
    result = capture_correction(
        correction="Always lead with the agency's craft, not the metrics.",
        source="chat:test:turn-1",
        skill_tags=["draft-composer", "general"],
        role_tags=["chief-of-staff"],
    )
    assert result.rule_id
    assert "draft-composer" in result.skill_tags
    assert "general" in result.skill_tags
    assert result.recapture is None  # nothing similar yet

    db = get_db()
    row = db.execute(
        "SELECT correction FROM learning_rules WHERE id=?", (result.rule_id,)
    ).fetchone()
    db.close()
    assert row["correction"].startswith("Always lead")


@pytest.mark.seam
def test_capture_rejects_empty(tmp_agency):
    from _framework.learning import capture_correction
    with pytest.raises(ValueError):
        capture_correction(correction="", source="x", skill_tags=["foo"])
    with pytest.raises(ValueError):
        capture_correction(correction="x", source="", skill_tags=["foo"])
    with pytest.raises(ValueError):
        capture_correction(correction="x", source="y", skill_tags=[])


@pytest.mark.seam
def test_injection_returns_rule(tmp_agency):
    from _framework.learning import capture_correction, inject_for_skill
    capture_correction(
        correction="Never CC the board without a heads-up.",
        source="chat:test:1",
        skill_tags=["send-orchestrator"],
        role_tags=["chief-of-staff"],
    )
    text = inject_for_skill(
        skill_name="send-orchestrator",
        profile="loriah",
        role="chief-of-staff",
    )
    assert "Never CC the board" in text


@pytest.mark.seam
def test_injection_pulls_general(tmp_agency):
    from _framework.learning import capture_correction, inject_for_skill
    capture_correction(
        correction="We-not-I in all outbound voice.",
        source="chat:test:2",
        skill_tags=["general"],
        voice_tags=["we-not-i"],
    )
    text = inject_for_skill(
        skill_name="any-skill-at-all",
        profile="loriah",
        role="chief-of-staff",
    )
    assert "We-not-I" in text


@pytest.mark.seam
def test_injection_pulls_role_match(tmp_agency):
    from _framework.learning import capture_correction, inject_for_skill
    capture_correction(
        correction="Analysts cite their sources.",
        source="chat:test:3",
        skill_tags=["red-team"],
        role_tags=["analyst-judge"],
    )
    text = inject_for_skill(
        skill_name="dossier-builder",  # different skill, same role
        profile="lynda",
        role="analyst-judge",
    )
    assert "cite their sources" in text


@pytest.mark.seam
def test_injection_does_not_pull_other_role(tmp_agency):
    from _framework.learning import capture_correction, inject_for_skill
    capture_correction(
        correction="Writing's voice ≠ agency's voice.",
        source="chat:test:4",
        skill_tags=["book-coaching"],
        role_tags=["writing-support"],
    )
    text = inject_for_skill(
        skill_name="draft-composer",
        profile="loriah",
        role="chief-of-staff",
    )
    assert "Writing's voice" not in text


@pytest.mark.seam
def test_firing_records_and_counts(tmp_agency):
    from _framework.learning import capture_correction, record_firing
    from _framework.learning.firings import count_for_skill_in_days, for_rule

    res = capture_correction(
        correction="Pause before pressing send on a Friday.",
        source="chat:test:5",
        skill_tags=["send-orchestrator"],
    )
    fid = record_firing(
        rule_id=res.rule_id,
        skill_tag="send-orchestrator",
        profile="loriah",
        action_summary="held the message until Monday",
    )
    assert fid >= 1

    fires = for_rule(res.rule_id)
    assert len(fires) == 1
    assert fires[0].skill_tag == "send-orchestrator"

    n = count_for_skill_in_days("send-orchestrator", days=7)
    assert n == 1


@pytest.mark.seam
def test_recapture_detects_repeat_correction(tmp_agency):
    """The canary: capture the same correction twice → recapture fires."""
    from _framework.learning import capture_correction
    # First capture
    capture_correction(
        correction="Never quote injection trigger phrases verbatim. Paraphrase only.",
        source="chat:test:6",
        skill_tags=["prompt-injection-defense"],
    )
    time.sleep(0.01)  # ensure created_at ordering
    # Second, similar correction — same source would dedupe by id, so vary source
    result2 = capture_correction(
        correction="Never quote injection trigger phrases verbatim. Paraphrase only.",
        source="chat:test:7",
        skill_tags=["prompt-injection-defense"],
    )
    assert result2.recapture is not None
    assert result2.recapture.similarity > 0.85


@pytest.mark.seam
def test_recapture_dismissal_blocks_future_alert(tmp_agency):
    from _framework.learning import capture_correction
    from _framework.learning.recapture_detector import dismiss_recapture
    r1 = capture_correction(
        correction="Use plain language, not consultant jargon.",
        source="chat:test:8",
        skill_tags=["draft-composer"],
    )
    time.sleep(0.01)
    r2 = capture_correction(
        correction="Use plain language, not consultant jargon.",
        source="chat:test:9",
        skill_tags=["draft-composer"],
    )
    assert r2.recapture is not None
    dismiss_recapture(r1.rule_id, r2.recapture.similar_to or r1.rule_id, note="false-positive")

    # A third capture of the same correction with a NEW source should still fire,
    # but if denylisted with the prior, the denylist takes effect when SAME pair.
    # Capture a third — it'll be similar to BOTH; but pair (r3, r1) and (r3, r2)
    # are not denylisted, so we expect a recapture against r2 (most recent).
    r3 = capture_correction(
        correction="Use plain language, not consultant jargon.",
        source="chat:test:10",
        skill_tags=["draft-composer"],
    )
    # The denylist blocks the (r1, r2) pair, not r3-anything; r3 should still fire
    assert r3.recapture is not None


@pytest.mark.seam
def test_hard_rule_is_marked(tmp_agency):
    from _framework.learning import capture_correction
    from _framework.learning.learning_db import get_db
    res = capture_correction(
        correction="Never send to recipients on the blacklist.",
        source="chat:test:11",
        skill_tags=["send-orchestrator"],
        is_hard=True,
    )
    db = get_db()
    row = db.execute("SELECT is_hard FROM learning_rules WHERE id=?", (res.rule_id,)).fetchone()
    db.close()
    assert int(row["is_hard"]) == 1


@pytest.mark.seam
def test_compliance_report_generates(tmp_agency):
    from _framework.learning import capture_correction, record_firing
    from _framework.learning.compliance_report import generate

    r = capture_correction(
        correction="A correction that fires.",
        source="chat:test:cr1",
        skill_tags=["draft-composer"],
    )
    record_firing(r.rule_id, "draft-composer", "loriah", action_summary="applied")

    report = generate()
    assert report.rules_captured_this_week >= 1
    assert any(rec["id"] == r.rule_id for rec in report.sample_recent_corrections)
    md = report.to_markdown()
    assert "Weekly compliance report" in md
    assert "Capture" in md
    assert "Firing" in md
    assert "Recapture" in md
