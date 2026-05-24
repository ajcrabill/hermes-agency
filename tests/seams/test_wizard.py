"""Wizard seam tests — exercise the non-interactive path with a mock prompter."""

from __future__ import annotations

import pytest


def _scripted_prompter(answers: dict[str, str]):
    """Return a prompter that answers each question by lookup, else returns the default."""
    def prompt(question: str, default: str) -> str:
        # Match by substring of question
        for needle, value in answers.items():
            if needle.lower() in question.lower():
                return value or default
        return default
    return prompt


@pytest.mark.seam
def test_tier1_writes_validated_manifest(tmp_agency):
    from _framework.ops.init import run_wizard
    from _framework.constants import DEPLOYMENT_YAML
    from _framework.manifest import validate

    prompter = _scripted_prompter({
        "Owner handle": "j-doe",
        "Organization name": "Jane Doe Consulting",
        "primary email": "jane@example.com",
        "Timezone": "America/Chicago",
        "Provider id": "ollama",
        "Model id": "qwen2.5-coder:7b",
        "Base URL": "http://localhost:11434/v1",
        "Credential reference": "env:OLLAMA_API_KEY",
        "CoS profile id": "cos",
        "CoS outbound email": "agency@example.com",
        "Knowledge Base profile id": "kb",
        "System Sentinel profile id": "sentinel",
    })

    rc = run_wizard(tier=1, prompter=prompter, force=True)
    assert rc == 0
    assert DEPLOYMENT_YAML.exists()
    result = validate(DEPLOYMENT_YAML)
    blocking = [f for f in result.errors if f.code != "profile-missing-soul"]
    assert not blocking, f"unexpected errors: {[str(f) for f in blocking]}"


@pytest.mark.seam
def test_wizard_refuses_overwrite_without_force(tmp_agency):
    from _framework.ops.init import run_wizard
    from _framework.constants import DEPLOYMENT_YAML

    # Pre-create a deployment.yaml so the second invocation should refuse
    DEPLOYMENT_YAML.write_text("placeholder: yes\n")
    prompter = _scripted_prompter({})
    rc = run_wizard(tier=1, prompter=prompter, force=False)
    assert rc == 1


@pytest.mark.seam
def test_wizard_scaffolds_three_required_profiles(tmp_agency):
    from _framework.ops.init import run_wizard
    from _framework.constants import profile_soul, profile_standards

    prompter = _scripted_prompter({
        "Owner handle": "test-owner",
        "Organization name": "Test Org",
        "primary email": "test@example.com",
        "Timezone": "America/Chicago",
        "Provider id": "ollama",
        "Model id": "qwen2.5",
        "Base URL": "http://localhost:11434/v1",
        "Credential reference": "env:OLLAMA_API_KEY",
        "CoS profile id": "cos",
        "CoS outbound email": "agency@example.com",
        "Knowledge Base profile id": "kb",
        "System Sentinel profile id": "sentinel",
    })
    rc = run_wizard(tier=1, prompter=prompter, force=True)
    assert rc == 0
    for pid in ("cos", "kb", "sentinel"):
        assert profile_soul(pid).exists(), f"missing SOUL.md for {pid}"
        assert profile_standards(pid).exists(), f"missing standards.md for {pid}"
