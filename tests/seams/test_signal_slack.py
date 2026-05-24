"""Signal + Slack integration tests — config + module shape (no live calls)."""

from __future__ import annotations

import json
import pytest


# ── Signal ──────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_signal_not_configured_by_default(tmp_agency):
    from _framework.integrations.signal import is_configured
    assert is_configured("any-profile") is False


@pytest.mark.seam
def test_signal_setup_writes_config(tmp_agency):
    from _framework.scaffolds import scaffold_profile
    from _framework.integrations.signal import (
        setup_interactive, is_configured, config_path,
    )
    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "T", "OWNER_NAME": "T",
        "COS_EMAIL": "x@example.com",
    })
    setup_interactive("cos", signal_number="+15551234567")
    assert is_configured("cos")
    raw = json.loads(config_path("cos").read_text())
    assert raw["signal_number"] == "+15551234567"


@pytest.mark.seam
def test_signal_poll_requires_configured(tmp_agency):
    from _framework.integrations.signal import poll_messages
    with pytest.raises(RuntimeError, match="not configured"):
        poll_messages("not-set-up")


@pytest.mark.seam
def test_signal_send_requires_recipient(tmp_agency):
    from _framework.scaffolds import scaffold_profile
    from _framework.integrations.signal import setup_interactive, send_message
    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "T", "OWNER_NAME": "T",
        "COS_EMAIL": "x@example.com",
    })
    setup_interactive("cos", signal_number="+15551234567")
    with pytest.raises(ValueError, match="to_number or group_id"):
        send_message("cos", body="hi")


# ── Slack ───────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_slack_not_configured_by_default(tmp_agency):
    from _framework.integrations.slack import is_configured
    assert is_configured("any-profile") is False


@pytest.mark.seam
def test_slack_setup_writes_config(tmp_agency, monkeypatch):
    from _framework.scaffolds import scaffold_profile
    from _framework.integrations.slack import (
        setup_interactive, is_configured, config_path,
    )

    # Stub the API call so we don't hit the real Slack API
    def fake_api_call(method, *, token, **params):
        if method == "auth.test":
            return {"ok": True, "user_id": "U_BOT_123"}
        return {"ok": False}
    monkeypatch.setattr("_framework.integrations.slack._api_call", fake_api_call)

    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "T", "OWNER_NAME": "T",
        "COS_EMAIL": "x@example.com",
    })
    setup_interactive("cos", token="xoxb-test-token-123")
    assert is_configured("cos")
    raw = json.loads(config_path("cos").read_text())
    assert raw["bot_token"] == "xoxb-test-token-123"
    assert raw["bot_user_id"] == "U_BOT_123"


@pytest.mark.seam
def test_slack_send_requires_configured(tmp_agency):
    from _framework.integrations.slack import send_message
    with pytest.raises(RuntimeError, match="not configured"):
        send_message("not-set-up", channel="C123", text="hi")


@pytest.mark.seam
def test_slack_poll_returns_empty_on_api_failure(tmp_agency, monkeypatch):
    from _framework.scaffolds import scaffold_profile
    from _framework.integrations.slack import (
        setup_interactive, poll_messages,
    )

    # Make every API call fail
    def failing_api(method, *, token, **params):
        raise RuntimeError("api unavailable")
    # Setup with a passing stub first, then switch
    setup_calls = []
    def setup_api(method, *, token, **params):
        setup_calls.append(method)
        return {"ok": True, "user_id": "U_BOT"}
    monkeypatch.setattr("_framework.integrations.slack._api_call", setup_api)
    scaffold_profile(role="chief-of-staff", profile_id="cos", substitutions={
        "COS_NAME": "Cos", "ORG_NAME": "T", "OWNER_NAME": "T",
        "COS_EMAIL": "x@example.com",
    })
    setup_interactive("cos", token="xoxb-x")

    monkeypatch.setattr("_framework.integrations.slack._api_call", failing_api)
    messages = poll_messages("cos")
    assert messages == []   # gracefully degraded
