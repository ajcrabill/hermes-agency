"""
Manifest validator tests.

These exercise `_framework.manifest.validate()` across the failure
modes the validator is supposed to catch — both errors (blocking) and
warnings (non-blocking).
"""

from __future__ import annotations

import textwrap

import pytest


# ── Minimal valid manifest body used as the baseline ────────────────────

VALID_BODY = """
deployment:
  owner: "j-doe"
  org_name: "Jane Doe Consulting"
  primary_email: "jane@example.com"
  timezone: "America/Chicago"
  framework_version: "0.1.0"

profiles:
  - id: loriah
    role: chief-of-staff
    persona_file: identities/chief-of-staff.md
    email: "loriah@example.com"
    starter_skills: [draft-composer, send-orchestrator]
  - id: esby
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
  model: gpt-4o
  provider: openai
  base_url: https://api.openai.com/v1
  fallback_providers:
    - provider: ollama
      model: qwen2.5
      base_url: http://localhost:11434/v1

credentials:
  openai: "keychain:openai-key"

ingress:
  email: true
  chat_tab: true
  signal: false
  slack: false
  openwebui: false
"""


@pytest.mark.seam
def test_valid_manifest_passes(write_manifest):
    from _framework.manifest import validate
    path = write_manifest(VALID_BODY)
    result = validate(path)
    # SOUL.md missing on disk → critical errors expected; isolate the
    # validator surface by tolerating missing-soul findings in this test.
    blocking = [f for f in result.errors if f.code != "profile-missing-soul"]
    assert not blocking, f"unexpected errors: {[str(f) for f in blocking]}"


@pytest.mark.seam
def test_missing_manifest_errors(tmp_agency):
    from _framework.manifest import validate
    result = validate(tmp_agency / "deployment.yaml")  # not written
    assert not result.ok
    assert any(f.code == "manifest-not-found" for f in result.errors)


@pytest.mark.seam
def test_placeholder_left_in_errors(write_manifest):
    from _framework.manifest import validate
    body = VALID_BODY.replace("j-doe", "{{OWNER_HANDLE}}")
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "manifest-placeholder" for f in result.errors)


@pytest.mark.seam
def test_missing_required_role_errors(write_manifest):
    from _framework.manifest import validate
    # Drop the knowledge-base entry
    body = VALID_BODY.replace(
        """  - id: esby
    role: knowledge-base
    persona_file: identities/knowledge-base.md
    email: null
    starter_skills: [ip-curator]
""",
        "",
    )
    path = write_manifest(body)
    result = validate(path)
    assert any(
        f.code == "missing-required-role" and "knowledge-base" in f.message
        for f in result.errors
    )


@pytest.mark.seam
def test_inline_secret_errors(write_manifest):
    from _framework.manifest import validate
    body = VALID_BODY.replace(
        'openai: "keychain:openai-key"', 'openai: "sk-actual-key-value-12345"'
    )
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "credential-inline-secret" for f in result.errors)


@pytest.mark.seam
def test_unknown_provider_errors(write_manifest):
    from _framework.manifest import validate
    body = VALID_BODY.replace("provider: openai", "provider: fictional-provider")
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "default-provider-unknown" for f in result.errors)


@pytest.mark.seam
def test_duplicate_profile_id_errors(write_manifest):
    from _framework.manifest import validate
    body = VALID_BODY.replace("id: sentinel", "id: esby", 1)
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "duplicate-profile-id" for f in result.errors)


@pytest.mark.seam
def test_no_fallback_providers_warns(write_manifest):
    from _framework.manifest import validate
    body = textwrap.dedent(VALID_BODY).replace(
        """  fallback_providers:
    - provider: ollama
      model: qwen2.5
      base_url: http://localhost:11434/v1""",
        "  fallback_providers: []",
    )
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "no-fallback-providers" for f in result.warnings)


@pytest.mark.seam
def test_non_cos_mailbox_warns(write_manifest):
    from _framework.manifest import validate
    body = VALID_BODY.replace(
        "    email: null\n    starter_skills: [ip-curator]",
        '    email: "esby@example.com"\n    starter_skills: [ip-curator]',
        1,
    )
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "non-cos-mailbox" for f in result.warnings)


@pytest.mark.seam
def test_ingress_all_false_warns(write_manifest):
    from _framework.manifest import validate
    body = VALID_BODY.replace("email: true\n  chat_tab: true", "email: false\n  chat_tab: false")
    path = write_manifest(body)
    result = validate(path)
    assert any(f.code == "no-ingress" for f in result.warnings)
