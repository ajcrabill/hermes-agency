"""Two-tier quality + cost attribution + markdown projector + auth + auto-reapply."""

from __future__ import annotations

import pytest


# ── Quality ─────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_quality_score_records_overall_as_min(tmp_agency):
    from _framework.quality import score_artifact, list_scores
    sid = score_artifact(
        artifact_id="t-001", producer="writing-support:newsletter-drafting",
        dimensions={"clarity": 0.9, "specificity": 0.7, "voice_fidelity": 0.85},
    )
    scores = list_scores()
    assert len(scores) == 1
    assert scores[0].overall_score == 0.7   # min of dimensions


@pytest.mark.seam
def test_quality_rolling_score(tmp_agency):
    from _framework.quality import score_artifact, rolling_score
    producer = "p1"
    for s in [0.9, 0.85, 0.8, 0.95, 0.6]:
        score_artifact(
            artifact_id=f"a-{s}", producer=producer,
            dimensions={"d": s},
        )
    roll = rolling_score(producer, window=5)
    assert roll["count"] == 5
    assert roll["mean_score"] == pytest.approx(0.82, rel=0.01)


@pytest.mark.seam
def test_undelegation_verdict_trusted(tmp_agency):
    from _framework.quality import score_artifact, should_undelegate
    for s in [0.9, 0.9, 0.85, 0.9, 0.85]:
        score_artifact(artifact_id=f"a-{s}", producer="p", dimensions={"d": s})
    verdict = should_undelegate("p")
    assert verdict.proposed_state == "trusted"
    assert verdict.should_undelegate is False


@pytest.mark.seam
def test_undelegation_verdict_at_risk(tmp_agency):
    from _framework.quality import score_artifact, should_undelegate
    for s in [0.7, 0.75, 0.72, 0.68, 0.7]:
        score_artifact(artifact_id=f"a-{s}", producer="p", dimensions={"d": s})
    verdict = should_undelegate("p")
    assert verdict.proposed_state == "watching"


@pytest.mark.seam
def test_undelegation_verdict_below_threshold(tmp_agency):
    from _framework.quality import score_artifact, should_undelegate
    for s in [0.5, 0.55, 0.6, 0.45, 0.5]:
        score_artifact(artifact_id=f"a-{s}", producer="p", dimensions={"d": s})
    verdict = should_undelegate("p")
    assert verdict.proposed_state == "undelegated"
    assert verdict.should_undelegate is True


@pytest.mark.seam
def test_undelegation_not_enough_data(tmp_agency):
    from _framework.quality import score_artifact, should_undelegate
    score_artifact(artifact_id="a", producer="p", dimensions={"d": 0.3})
    verdict = should_undelegate("p")
    assert verdict.proposed_state == "trusted"   # default until enough data


# ── Cost ────────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_cost_pricer_registration_and_compute(tmp_agency):
    from _framework.cost.pricing import (
        register_pricer, compute_cost_cents, clear_pricers,
    )
    clear_pricers()
    register_pricer(
        provider="openai-compat", model="gpt-x-fast",
        tokens_in_per_million_cents=15,
        tokens_out_per_million_cents=60,
    )
    # 1M input tokens → 15 cents; 0.5M output → 30 cents
    cost = compute_cost_cents(provider="openai-compat", model="gpt-x-fast",
                                tokens_in=1_000_000, tokens_out=500_000)
    assert cost == pytest.approx(45.0)


@pytest.mark.seam
def test_cost_pricer_wildcard_fallback(tmp_agency):
    from _framework.cost.pricing import (
        register_pricer, compute_cost_cents, clear_pricers,
    )
    clear_pricers()
    register_pricer(provider="ollama", model="*",
                     tokens_in_per_million_cents=0,
                     tokens_out_per_million_cents=0)
    cost = compute_cost_cents(provider="ollama", model="any-local-model",
                                tokens_in=1_000_000, tokens_out=1_000_000)
    assert cost == 0.0


@pytest.mark.seam
def test_cost_record_and_rollup(tmp_agency):
    from _framework.cost import (
        record_inference_call, skill_totals, role_totals,
    )
    from _framework.cost.pricing import register_pricer, clear_pricers
    clear_pricers()
    register_pricer(provider="openai-compat", model="gpt-x",
                     tokens_in_per_million_cents=10,
                     tokens_out_per_million_cents=30)
    record_inference_call(
        skill="draft-composer", profile="cos", role="chief-of-staff",
        provider="openai-compat", model="gpt-x",
        tokens_in=10_000, tokens_out=5_000,
    )
    record_inference_call(
        skill="draft-composer", profile="cos", role="chief-of-staff",
        provider="openai-compat", model="gpt-x",
        tokens_in=20_000, tokens_out=10_000,
    )
    skills = skill_totals()
    assert len(skills) == 1
    assert skills[0]["skill"] == "draft-composer"
    assert skills[0]["n"] == 2
    assert skills[0]["tin"] == 30_000
    assert skills[0]["tout"] == 15_000

    roles = role_totals()
    assert len(roles) == 1
    assert roles[0]["role"] == "chief-of-staff"


@pytest.mark.seam
def test_cost_budget_check(tmp_agency):
    from _framework.cost import (
        record_inference_call, set_budget, check_budget,
    )
    from _framework.cost.pricing import register_pricer, clear_pricers
    clear_pricers()
    register_pricer(provider="x", model="y",
                     tokens_in_per_million_cents=1000,
                     tokens_out_per_million_cents=1000)
    set_budget(period="monthly", limit_micro=100_000,   # = 10 cents
                skill="draft-composer")
    # Push the spending above 10c
    record_inference_call(
        skill="draft-composer", provider="x", model="y",
        tokens_in=200_000, tokens_out=0,  # 200,000/1,000,000 * 1000 cents = 200 cents
    )
    verdict = check_budget(skill="draft-composer", period="monthly")
    assert verdict.over_budget is True


# ── Markdown projector ─────────────────────────────────────────────────


@pytest.mark.seam
def test_markdown_projector_runs_with_no_data(tmp_agency):
    from _framework.state.markdown_projector import project_all, list_projectors
    assert "learning" in list_projectors()
    assert "goals" in list_projectors()
    assert "finance" in list_projectors()
    assert "prototypes" in list_projectors()
    results = project_all()
    # All return 0 files when DBs are empty/absent — that's OK
    assert all(v >= 0 for v in results.values())


@pytest.mark.seam
def test_markdown_projector_projects_goals(tmp_agency):
    from _framework.goals import define_metric, record_observation
    from _framework.state.markdown_projector import project_one
    from _framework.constants import AGENCY_VAULT
    mid = define_metric(
        goal_text="Test goal", metric_name="test_metric",
        measurement_type="counter", target_value=10,
        target_at="2026-12-31",
    )
    record_observation(metric_id=mid, value=3)
    n = project_one("goals")
    assert n == 1
    projected = (AGENCY_VAULT / "projections" / "goals" / "tracking.md")
    assert projected.exists()
    text = projected.read_text(encoding="utf-8")
    assert "test_metric" in text


# ── Auth (OTP) ──────────────────────────────────────────────────────────


@pytest.mark.seam
def test_otp_issue_verify_happy_path(tmp_agency):
    from _framework.ops.auth import issue_otp, verify_otp, validate_session
    challenge, code = issue_otp(email="owner@example.com")
    assert len(code) == 6
    session = verify_otp(challenge_id=challenge.challenge_id, code=code)
    assert session is not None
    assert session.email == "owner@example.com"
    # The session token validates
    assert validate_session(session.token) is not None


@pytest.mark.seam
def test_otp_wrong_code_rejected(tmp_agency):
    from _framework.ops.auth import issue_otp, verify_otp
    challenge, code = issue_otp(email="owner@example.com")
    wrong = "000000" if code != "000000" else "111111"
    assert verify_otp(challenge_id=challenge.challenge_id, code=wrong) is None


@pytest.mark.seam
def test_otp_max_attempts_lockout(tmp_agency):
    from _framework.ops.auth import issue_otp, verify_otp, OTP_MAX_ATTEMPTS
    challenge, code = issue_otp(email="owner@example.com")
    for _ in range(OTP_MAX_ATTEMPTS):
        verify_otp(challenge_id=challenge.challenge_id, code="000000")
    # Even the correct code now fails
    assert verify_otp(challenge_id=challenge.challenge_id, code=code) is None


@pytest.mark.seam
def test_session_revocation(tmp_agency):
    from _framework.ops.auth import issue_otp, verify_otp, revoke_session, validate_session
    challenge, code = issue_otp(email="x@example.com")
    session = verify_otp(challenge_id=challenge.challenge_id, code=code)
    assert validate_session(session.token) is not None
    revoke_session(session.token)
    assert validate_session(session.token) is None


# ── Auto-reapply ────────────────────────────────────────────────────────


@pytest.mark.seam
def test_auto_reapply_needs_when_no_lock(tmp_agency):
    from _framework.hermes_patches.auto_reapply import needs_reapply
    needs, reason = needs_reapply()
    assert needs is True
    assert "no prior apply" in reason


@pytest.mark.seam
def test_auto_reapply_detects_no_change(tmp_agency, monkeypatch):
    from _framework.hermes_patches.auto_reapply import (
        write_lock, fingerprint_targets, needs_reapply,
    )

    # Stub Hermes install with one target file
    hermes_home = tmp_agency.parent / ".hermes-reapply-test"
    hermes_agent = hermes_home / "hermes-agent" / "agent"
    hermes_agent.mkdir(parents=True)
    target = hermes_agent / "skill_commands.py"
    target.write_text(
        "def _inject_skill_config(loaded_skill, parts):\n    pass\n"
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    # Compute fingerprint + write lock
    write_lock(["skill_load_injection"])
    needs, reason = needs_reapply()
    assert needs is False
    assert "match" in reason


@pytest.mark.seam
def test_auto_reapply_detects_change(tmp_agency, monkeypatch):
    from _framework.hermes_patches.auto_reapply import (
        write_lock, needs_reapply,
    )
    hermes_home = tmp_agency.parent / ".hermes-changed"
    hermes_agent = hermes_home / "hermes-agent" / "agent"
    hermes_agent.mkdir(parents=True)
    target = hermes_agent / "skill_commands.py"
    target.write_text("def _inject_skill_config(loaded_skill, parts):\n    pass\n")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    write_lock(["skill_load_injection"])
    # Simulate Hermes upgrade — rewrite the target
    target.write_text("def _inject_skill_config(loaded_skill, parts):\n    return 'changed'\n")
    needs, reason = needs_reapply()
    assert needs is True
    assert "fingerprint changed" in reason
