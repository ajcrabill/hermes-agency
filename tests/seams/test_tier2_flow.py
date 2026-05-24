"""Tier 2 interactive flow tests — scripted prompter, stub integration setup."""

from __future__ import annotations

import yaml
import pytest


_VALID_MANIFEST = """\
deployment:
  owner: "test"
  org_name: "Test"
  primary_email: "x@example.com"
  timezone: "America/Chicago"
  framework_version: "0.1.0"

profiles:
  - id: cos
    role: chief-of-staff
    persona_file: identities/chief-of-staff.md
    email: agency@example.com
    starter_skills: [draft-composer]
  - id: kb
    role: knowledge-base
    persona_file: identities/knowledge-base.md
    email: null
    starter_skills: [ip-curator]
  - id: sentinel
    role: system-sentinel
    persona_file: identities/system-sentinel.md
    email: null
    starter_skills: [learning-monitor]

defaults:
  model: qwen2.5
  provider: ollama
  base_url: http://localhost:11434/v1
  fallback_providers: []

credentials:
  ollama: "env:OLLAMA_API_KEY"

ingress:
  email: true
  chat_tab: true
  signal: false
  slack: false
"""


def _scripted(answers: dict[str, str]):
    """Map fragment-of-question → answer."""
    def _p(q: str, default: str, hint: str) -> str:
        for k, v in answers.items():
            if k.lower() in q.lower():
                return v if v != "" else default
        return default
    return _p


def _stub_integration(_name: str, _profile: str, *, client_secret: str) -> None:
    """No-op stub for integration setup — tests don't exercise real OAuth."""
    if not client_secret:
        raise ValueError("no client_secret")


@pytest.mark.seam
def test_tier2_runs_with_all_defaults(tmp_agency):
    from _framework.constants import DEPLOYMENT_YAML
    DEPLOYMENT_YAML.write_text(_VALID_MANIFEST)

    from _framework.ops.init.tier2_flow import run_tier2_flow

    prompter = _scripted({})  # everything defaults
    answers = run_tier2_flow(
        cos_id="cos",
        prompter=prompter,
        setup_integration=_stub_integration,
    )
    # Defaults defer all integrations
    assert "gmail" in answers.deferred_steps
    assert "calendar" in answers.deferred_steps
    assert "drive" in answers.deferred_steps
    # Ingress: email + chat-tab on, others off
    assert answers.ingress_email is True
    assert answers.ingress_signal is False


@pytest.mark.seam
def test_tier2_persists_to_deployment_yaml(tmp_agency):
    from _framework.constants import DEPLOYMENT_YAML
    DEPLOYMENT_YAML.write_text(_VALID_MANIFEST)
    from _framework.ops.init.tier2_flow import run_tier2_flow

    prompter = _scripted({
        "Morning briefing time": "07:30",
        "Triage batch times": "07:30,12:00,18:00",
        "dashboard chat-tab": "y",
        "Signal": "y",
    })
    run_tier2_flow(
        cos_id="cos",
        prompter=prompter,
        setup_integration=_stub_integration,
    )
    doc = yaml.safe_load(DEPLOYMENT_YAML.read_text())
    assert doc["tier2"]["morning_briefing_time"] == "07:30"
    assert doc["tier2"]["daily_batch_times"] == ["07:30", "12:00", "18:00"]
    assert doc["ingress"]["signal"] is True
    assert doc["ingress"]["chat_tab"] is True


@pytest.mark.seam
def test_tier2_runs_gmail_setup_when_yes(tmp_agency):
    from _framework.constants import DEPLOYMENT_YAML
    DEPLOYMENT_YAML.write_text(_VALID_MANIFEST)
    from _framework.ops.init.tier2_flow import run_tier2_flow

    called = []
    def _spy(name, profile, *, client_secret):
        called.append((name, profile, client_secret))

    prompter = _scripted({
        "Gmail OAuth": "y",
        "client_secret.json": "/fake/path/cs.json",
        "scope preset": "send",
    })
    answers = run_tier2_flow(
        cos_id="cos",
        prompter=prompter,
        setup_integration=_spy,
    )
    assert called
    # First call should be Gmail setup
    assert called[0][0] == "gmail"
    assert called[0][1] == "cos"
    assert "gmail" not in answers.deferred_steps


@pytest.mark.seam
def test_tier2_ingest_sources_captured(tmp_agency):
    from _framework.constants import DEPLOYMENT_YAML
    DEPLOYMENT_YAML.write_text(_VALID_MANIFEST)
    from _framework.ops.init.tier2_flow import run_tier2_flow

    # Scripted: one RSS source, then stop
    seq = iter([
        ("rss", ""),
        ("https://example.com/feed.xml", ""),
        ("Example Feed", ""),
        ("none-stop", ""),
    ])
    def p(q: str, default: str, hint: str) -> str:
        if "Add an ingest source" in q:
            return "rss"
        if "Source URL" in q:
            return "https://example.com/feed.xml"
        if "Display name" in q:
            return "Example Feed"
        return default
    # On the second pass through the loop, it'll ask "Add an ingest
    # source" again — return "none-stop" to break out
    call_counts = {"add_source": 0}
    def p2(q: str, default: str, hint: str) -> str:
        if "Add an ingest source" in q:
            call_counts["add_source"] += 1
            return "rss" if call_counts["add_source"] == 1 else "none-stop"
        if "Source URL" in q:
            return "https://example.com/feed.xml"
        if "Display name" in q:
            return "Example Feed"
        return default

    answers = run_tier2_flow(
        cos_id="cos",
        prompter=p2,
        setup_integration=_stub_integration,
    )
    assert len(answers.ingest_sources) == 1
    assert answers.ingest_sources[0]["url"] == "https://example.com/feed.xml"
    assert answers.ingest_sources[0]["name"] == "Example Feed"
