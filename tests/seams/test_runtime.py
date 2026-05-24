"""Seam tests for the runtime subsystem (provider resolution + prompt
composition). The HTTP call itself in chat_once is integration-only
(needs network + a real provider key) so we don't exercise it here.

Note: tmp_agency clears sys.modules for _framework so per-test imports
need to happen INSIDE the test function (after the fixture runs).
"""

from __future__ import annotations

import pytest


# ── Credential resolution ────────────────────────────────────────────
# These don't need tmp_agency, just monkeypatch.


def test_cred_dash_is_empty():
    from _framework.runtime.provider import _resolve_cred_ref
    assert _resolve_cred_ref("-") == ""
    assert _resolve_cred_ref("env:NONE") == ""


def test_cred_env_resolves_from_process_env(monkeypatch):
    from _framework.runtime.provider import _resolve_cred_ref
    monkeypatch.setenv("FAKE_KEY_XYZ", "sk-faketoken")
    assert _resolve_cred_ref("env:FAKE_KEY_XYZ") == "sk-faketoken"


def test_cred_env_falls_back_to_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("FAKE_KEY_XYZ", raising=False)
    fake_home = tmp_path / "agency-home"
    fake_home.mkdir()
    (fake_home / ".env").write_text(
        "# top comment\n"
        "FAKE_KEY_XYZ=from-dotenv\n"
        'QUOTED_KEY="quoted-value"\n'
        "EMPTY=\n",
    )
    from _framework.runtime import provider as p
    monkeypatch.setattr(p, "AGENCY_HOME", fake_home)
    assert p._read_dotenv_var("FAKE_KEY_XYZ") == "from-dotenv"
    assert p._read_dotenv_var("QUOTED_KEY") == "quoted-value"
    assert p._read_dotenv_var("MISSING") == ""


def test_cred_refuses_raw_secrets():
    from _framework.runtime.provider import _resolve_cred_ref, ProviderResolveError
    with pytest.raises(ProviderResolveError):
        _resolve_cred_ref("sk-13bce52c46e1446ca209d6d663ece64a")


def test_cred_file_ref(tmp_path):
    from _framework.runtime.provider import _resolve_cred_ref
    f = tmp_path / "key"
    f.write_text("secret-from-file\n")
    assert _resolve_cred_ref(f"file:{f}") == "secret-from-file"


def test_cred_file_ref_missing(tmp_path):
    from _framework.runtime.provider import _resolve_cred_ref, ProviderResolveError
    with pytest.raises(ProviderResolveError):
        _resolve_cred_ref(f"file:{tmp_path / 'nope'}")


# ── Prompt composition ──────────────────────────────────────────────
# These need tmp_agency, so imports happen INSIDE the test functions
# (after the fixture has cleared sys.modules + set the env var).


def test_compose_with_no_soul_or_standards(tmp_agency):
    """If no SOUL or standards files exist, prompt still builds with
    a fallback identity line."""
    from _framework.runtime.prompt import compose_chat_prompt
    composed = compose_chat_prompt(profile="loriah", role="chief-of-staff")
    assert "loriah" in composed.system
    assert composed.profile_used == "loriah"


def test_compose_includes_soul_when_present(tmp_agency):
    from _framework.constants import profile_soul, profile_dir
    pdir = profile_dir("loriah")
    pdir.mkdir(parents=True, exist_ok=True)
    soul = profile_soul("loriah")
    soul.write_text("I am Loriah, AJ's chief of staff. I am calm and decisive.")

    from _framework.runtime.prompt import compose_chat_prompt
    composed = compose_chat_prompt(profile="loriah", role="chief-of-staff")
    assert "I am Loriah" in composed.system
    assert "calm and decisive" in composed.system


def test_compose_includes_standards_when_present(tmp_agency):
    from _framework.constants import profile_standards, profile_dir
    pdir = profile_dir("loriah")
    pdir.mkdir(parents=True, exist_ok=True)
    stds = profile_standards("loriah")
    stds.write_text("# Stewardship\n\nNever send to clients on weekends.")

    from _framework.runtime.prompt import compose_chat_prompt
    composed = compose_chat_prompt(profile="loriah", role="chief-of-staff")
    assert "Stewardship" in composed.system
    assert "weekends" in composed.system


def test_compose_includes_session_framing(tmp_agency):
    from _framework.runtime.prompt import compose_chat_prompt
    composed = compose_chat_prompt(profile="loriah", role="chief-of-staff")
    assert "interactive chat" in composed.system.lower()
    assert "supervised-learning rules" in composed.system or "supervised learning" in composed.system.lower()
