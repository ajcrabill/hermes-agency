"""Autonomy + graduation gate tests."""

from __future__ import annotations

import pytest


@pytest.mark.seam
def test_skill_starts_at_l1(tmp_agency):
    from _framework.autonomy import get_skill_level
    assert get_skill_level("any-skill", "any-profile") == 1


@pytest.mark.seam
def test_clean_runs_promote_after_threshold(tmp_agency):
    from _framework.autonomy import record_event, get_skill_level
    # Default threshold is 5 (invariants.yaml::autonomy_promotion.consecutive_clean_runs)
    for _ in range(4):
        result = record_event("foo-skill", "loriah", "clean_run")
        # no promotion yet; counter is incrementing
    result = record_event("foo-skill", "loriah", "clean_run")  # 5th
    assert result is not None
    assert hasattr(result, "from_level") and result.from_level == 1
    assert result.to_level == 2
    assert get_skill_level("foo-skill", "loriah") == 2


@pytest.mark.seam
def test_failure_demotes_one_level(tmp_agency):
    from _framework.autonomy import record_event, set_skill_level, get_skill_level
    set_skill_level("bar-skill", "loriah", 3)
    result = record_event("bar-skill", "loriah", "failure", payload={"reason": "verifier-failed"})
    assert result.to_level == 2
    assert get_skill_level("bar-skill", "loriah") == 2


@pytest.mark.seam
def test_failure_floor_at_l1(tmp_agency):
    from _framework.autonomy import record_event, get_skill_level
    record_event("baz-skill", "loriah", "failure")
    assert get_skill_level("baz-skill", "loriah") == 1


@pytest.mark.seam
def test_action_class_lookup(tmp_agency):
    from _framework.autonomy import get_action_class_min_level
    assert get_action_class_min_level("draft-only") == 1
    assert get_action_class_min_level("send-batched") == 2
    assert get_action_class_min_level("send-single") == 3
    assert get_action_class_min_level("structural-change") == 4
    assert get_action_class_min_level("auto-irreversible") == 5


@pytest.mark.seam
def test_graduation_blocked_by_recapture(tmp_agency):
    """If recapture events implicate the skill, promotion blocks."""
    import time
    from _framework.learning import capture_correction
    from _framework.autonomy import record_event, get_skill_level

    # Capture two similar corrections under the same skill → recapture fires
    capture_correction(
        correction="The same thing said twice.",
        source="chat:1",
        skill_tags=["promote-me"],
    )
    time.sleep(0.01)
    capture_correction(
        correction="The same thing said twice.",
        source="chat:2",
        skill_tags=["promote-me"],
    )

    # Now hammer clean runs at the threshold
    blocked_result = None
    for _ in range(5):
        r = record_event("promote-me", "loriah", "clean_run")
        if r:
            blocked_result = r

    assert blocked_result is not None
    assert blocked_result.blocked is True
    assert blocked_result.blocker == "learning_blocked_promote"
    assert get_skill_level("promote-me", "loriah") == 1   # parked


@pytest.mark.seam
def test_graduation_blocked_by_dead_rules(tmp_agency):
    """If skill has >3 rules but no firings, promotion blocks."""
    from _framework.learning import capture_correction
    from _framework.autonomy import record_event, get_skill_level

    for i in range(4):
        capture_correction(
            correction=f"Rule number {i} for the skill",
            source=f"chat:{i}",
            skill_tags=["dead-loop-skill"],
        )

    blocked_result = None
    for _ in range(5):
        r = record_event("dead-loop-skill", "loriah", "clean_run")
        if r:
            blocked_result = r
    assert blocked_result is not None
    assert blocked_result.blocked is True
    assert blocked_result.blocker == "learning_blocked_promote"
    assert get_skill_level("dead-loop-skill", "loriah") == 1


@pytest.mark.seam
def test_graduation_passes_when_clean(tmp_agency):
    """No recapture, no dead rules, no audit findings → promotion happens."""
    from _framework.learning import capture_correction, record_firing
    from _framework.autonomy import record_event, get_skill_level

    # One rule + one firing → not a dead loop
    r = capture_correction(
        correction="Use plain language.",
        source="chat:plain",
        skill_tags=["clean-skill"],
    )
    record_firing(r.rule_id, "clean-skill", "loriah", action_summary="applied")

    promotion = None
    for _ in range(5):
        result = record_event("clean-skill", "loriah", "clean_run")
        if result:
            promotion = result
    assert promotion is not None
    assert promotion.blocked is False
    assert promotion.to_level == 2
    assert get_skill_level("clean-skill", "loriah") == 2


@pytest.mark.seam
def test_demote_passthrough(tmp_agency):
    from _framework.autonomy import set_skill_level, demote, get_skill_level
    set_skill_level("foo", "loriah", 4)
    d = demote("foo", "loriah", reason="manual rollback")
    assert d.to_level == 3
    assert get_skill_level("foo", "loriah") == 3
