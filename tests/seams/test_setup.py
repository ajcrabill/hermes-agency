"""Seam tests for the /agency setup interactive interview.

Tests the state machine + the clean-install flow end-to-end. The
migration path is tested separately in test_v7_migration.py — here
we just verify the dispatch works.
"""

from __future__ import annotations

import pytest


def _import_clean(tmp_path):
    """Force a clean import of the setup module under a fresh AGENCY_HOME."""
    import os, sys
    os.environ["HOME"] = str(tmp_path)
    os.environ["AGENCY_HOME"] = str(tmp_path / ".agency")
    for mod in [m for m in list(sys.modules) if "hermes_agency_plugin" in m]:
        del sys.modules[mod]


def test_setup_initial_prompt_shows_both_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command
    out = handle_setup_command("")
    assert "migrate" in out.lower()
    assert "clean" in out.lower()


def test_setup_clean_install_advances_through_questions(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    (tmp_path / ".agency" / "deployment.yaml").write_text("""
profiles:
  - id: loriah
    role: chief-of-staff
""")
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    # Start clean install
    out = handle_setup_command("clean")
    assert "question 1 of 8" in out.lower()

    # Walk through all 8 questions with quick answers
    answers = [
        "AJ Crabill",                    # owner_name
        "Good Ancestor",                 # org_name
        "AI Developer + governance writer",   # role_description
        "Ship v0.19; finish manuscript; sleep 7+ hours/night",  # current_goals
        "honesty, craft, long-term thinking, being a good ancestor",  # values
        "Two kids, work-from-home, no meetings before 9am",  # personal_context
        "CGCS, ESB, internal projects",  # clients
        "Short paragraphs; no exclamation marks; specifics over abstractions",  # voice_notes
    ]
    for i, answer in enumerate(answers):
        response = handle_setup_command(f"answer {answer}")
        if i < len(answers) - 1:
            # Should still be asking more questions
            assert "question" in response.lower(), f"step {i+1}: {response}"
        else:
            # Last answer → finalization
            assert "complete" in response.lower()
            assert "configured" in response.lower()

    # Deployment should now be configured
    assert is_configured()


def test_setup_skip_answer_works(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    handle_setup_command("clean")
    for _ in range(8):
        handle_setup_command("answer skip")
    # Should have marked configured even with all skips
    assert is_configured()


def test_setup_status(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command
    out = handle_setup_command("status")
    assert "not started" in out.lower() or "configured" in out.lower()


def test_setup_already_configured_blocks_re_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency").mkdir(parents=True)
    (tmp_path / ".agency" / ".configured").touch()
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command
    out = handle_setup_command("")
    assert "already configured" in out.lower()


def test_setup_reset_clears_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command
    # Begin a clean install
    handle_setup_command("clean")
    handle_setup_command("answer Test User")
    # Reset
    out = handle_setup_command("reset")
    assert "cleared" in out.lower() or "start over" in out.lower()
    # Should be back to initial
    out2 = handle_setup_command("")
    assert "migrate" in out2.lower()


def test_setup_migrate_requires_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command
    out = handle_setup_command("migrate")
    assert "needs a path" in out.lower() or "usage" in out.lower()


def test_setup_resume_after_partial(tmp_path, monkeypatch):
    """Mid-interview, calling `/agency setup` re-shows the current question."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command
    handle_setup_command("clean")
    handle_setup_command("answer First Answer")
    handle_setup_command("answer Second Answer")
    # Now bare /agency setup should re-prompt at question 3
    out = handle_setup_command("")
    assert "question 3" in out.lower()


def test_setup_routed_via_agency_slash_command(tmp_path, monkeypatch):
    """The /agency setup command dispatches through commands.py correctly."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    _import_clean(tmp_path)
    from hermes_agency_plugin.commands import handle_agency_command
    out = handle_agency_command("setup")
    assert "migrate" in out.lower() or "clean" in out.lower()
