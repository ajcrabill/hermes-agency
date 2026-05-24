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
        "AJ Crabill",                    # principal_name
        "Good Ancestor",                 # org_name
        "Technological-intelligence developer + governance writer",   # role_description
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
            # v0.23.5: Last answer → rough-draft preview + approval
            # gate. .configured is NOT written yet.
            assert "rough draft" in response.lower()
            assert "approve" in response.lower()
            assert not is_configured(), (
                "v0.23.5 approval gate violated: .configured was "
                "written before the Principal approved the draft."
            )

    # Principal approves the draft → finalize writes vault + marker
    final = handle_setup_command("approve")
    assert "complete" in final.lower()
    assert "configured" in final.lower()

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
    # v0.23.5: Skipping all answers still hits the approval gate;
    # `.configured` isn't written until the Principal approves.
    assert not is_configured()
    handle_setup_command("approve")
    # Now the deployment is marked configured
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


# ── v0.23.5 approval-gate tests ────────────────────────────────────────


def _walk_to_approval_gate(handle, principal_name="AJ Crabill"):
    """Helper: run an 8-answer clean install up to the approval gate
    without crossing it."""
    handle("clean")
    answers = [
        principal_name,                            # principal_name
        "Good Ancestor",                           # org_name
        "Technological-intelligence developer",    # role_description
        "Ship v0.23; finish manuscript",           # current_goals
        "honesty, craft, long-term thinking",      # values (Guardrails)
        "Two kids, no meetings before 9am",        # personal_context
        "CGCS, ESB",                               # clients
        "Short paragraphs; no exclamation marks",  # voice_notes
    ]
    response = ""
    for a in answers:
        response = handle(f"answer {a}")
    return response


def test_setup_last_answer_presents_rough_draft_not_finalize(tmp_path, monkeypatch):
    """v0.23.5: the 8th answer transitions to AWAITING_APPROVAL,
    presents the rough draft, and does NOT write .configured."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    response = _walk_to_approval_gate(handle_setup_command)
    assert "rough draft" in response.lower()
    assert "approve" in response.lower()
    assert "revise" in response.lower()
    # Principal sees what the CoS heard
    assert "good ancestor" in response.lower()
    assert "lines you won't cross" in response.lower()
    # Critical: .configured is NOT written yet
    assert not is_configured()


def test_setup_approve_finalizes_and_writes_configured(tmp_path, monkeypatch):
    """v0.23.5: /agency setup approve completes the install."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    _walk_to_approval_gate(handle_setup_command)
    out = handle_setup_command("approve")
    assert "complete" in out.lower()
    assert is_configured()


def test_setup_approve_without_pending_draft_errors(tmp_path, monkeypatch):
    """Approve before the gate is hit → friendly error, no marker."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    out = handle_setup_command("approve")
    assert "no draft" in out.lower() or "awaiting approval" in out.lower()
    assert not is_configured()


def test_setup_revise_updates_field_and_re_presents_draft(tmp_path, monkeypatch):
    """v0.23.5: revise <field> <new text> updates the answer + re-shows
    the draft with the new value."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    _walk_to_approval_gate(handle_setup_command)
    # Revise the goals field
    out = handle_setup_command(
        "revise goals Ship v0.24; double coaching revenue; sleep 7+ hrs"
    )
    assert "updated" in out.lower()
    assert "double coaching revenue" in out.lower()
    # Still NOT configured
    assert not is_configured()


def test_setup_revise_unknown_field_lists_valid_options(tmp_path, monkeypatch):
    """v0.23.5: revise <bogus> → friendly error listing valid fields."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command

    _walk_to_approval_gate(handle_setup_command)
    out = handle_setup_command("revise zzznotafield some text here")
    assert "unknown field" in out.lower() or "valid" in out.lower()
    assert "goals" in out.lower()  # listed as a valid field


def test_setup_revise_without_pending_draft_errors(tmp_path, monkeypatch):
    """Revise before the gate is hit → friendly error."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command

    out = handle_setup_command("revise goals New goals text")
    assert "no draft" in out.lower() or "start" in out.lower()


def test_setup_revise_then_approve_uses_new_value(tmp_path, monkeypatch):
    """v0.23.5: revise → approve uses the revised text in vault files."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command, is_configured

    _walk_to_approval_gate(handle_setup_command)
    handle_setup_command(
        "revise goals Revised goal text after deliberation"
    )
    handle_setup_command("approve")
    assert is_configured()
    # Find which vault location was used and check Goals.md
    new_home = tmp_path / ".hermes" / "agency-state" / "vaults" / "loriah"
    legacy_home = tmp_path / ".agency" / "profiles" / "loriah" / "vault"
    if new_home.exists() and (new_home / "Goals.md").exists():
        goals_md = (new_home / "Goals.md").read_text()
    else:
        goals_md = (legacy_home / "Goals.md").read_text()
    assert "Revised goal text after deliberation" in goals_md


def test_setup_revise_guardrails_alias(tmp_path, monkeypatch):
    """v0.23.5: `revise guardrails ...` is an alias for `revise values
    ...` since values → Guardrails.md in v0.23."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    (tmp_path / ".agency" / "profiles" / "loriah").mkdir(parents=True)
    _import_clean(tmp_path)
    from hermes_agency_plugin.setup import handle_setup_command

    _walk_to_approval_gate(handle_setup_command)
    out = handle_setup_command(
        "revise guardrails never compromise on craft or honesty"
    )
    assert "updated" in out.lower()
    assert "never compromise on craft" in out.lower()


# ── v0.23.5 strategic-planning-context loader ──────────────────────────


def test_strategic_planning_context_loads_or_stubs(tmp_path):
    """Module returns either §3 + §7.1 from StrategicPlanning.md, or
    the minimal SMART stub. Either way, the SMART canonical form is
    referenced."""
    from hermes_agency_plugin.setup.strategic_planning_context import (
        load_strategic_planning_context,
    )
    ctx = load_strategic_planning_context()
    assert ctx, "loader returned empty"
    assert "SMART" in ctx or "smart" in ctx.lower() or "Quality" in ctx


def test_strategic_planning_context_emits_stub_when_doc_missing(
    tmp_path, monkeypatch
):
    """If StrategicPlanning.md can't be located, the stub block is
    returned — the interview must always have something to ground on."""
    import sys
    for mod in [m for m in list(sys.modules) if "strategic_planning_context" in m]:
        del sys.modules[mod]
    from hermes_agency_plugin.setup import strategic_planning_context as spc

    # Replace probe paths with a guaranteed-nonexistent location
    monkeypatch.setattr(
        spc, "_PROBE_PATHS",
        [tmp_path / "nope" / "StrategicPlanning.md"],
    )
    ctx = spc.load_strategic_planning_context()
    assert "stub" in ctx.lower() or "SMART canonical form" in ctx
    assert "Outcomes" in ctx
    assert "Interim Goals" in ctx
    # Stub must also clarify the Guardrails vs Interim Guardrails
    # distinction (the critical v0.23.5 framing)
    assert "Guardrails" in ctx


def test_strategic_planning_context_extracts_section3_when_doc_present(
    tmp_path, monkeypatch
):
    """When StrategicPlanning.md exists at a probe path, §3 + §7.1
    are extracted."""
    import sys
    for mod in [m for m in list(sys.modules) if "strategic_planning_context" in m]:
        del sys.modules[mod]
    from hermes_agency_plugin.setup import strategic_planning_context as spc

    fake_doc = tmp_path / "docs" / "StrategicPlanning.md"
    fake_doc.parent.mkdir(parents=True)
    fake_doc.write_text("""# Strategic Planning

Some intro text.

## 1. Layers

Outcomes are SMART. Interim Goals are SMART. Initiatives are skills + scripts.

## 3. Quality criteria — what good Outcomes look like

An Outcome is a SMART statement: subject + measure, with a starting
point in a starting month/year and an ending point in an ending
month/year. The aim is parallel structure across all three layers.

## 7. File structure

### 7.1 Goals.md — the strategic document

Goals.md carries the three-layer structure: Outcomes → Interim Goals →
Initiative references. Initiatives are the skills + scripts that
produce outputs.

### 7.2 Guardrails.md

Guardrails are value statements; Interim Guardrails are SMART.

## 8. Other

Unrelated content.
""")

    monkeypatch.setattr(spc, "_PROBE_PATHS", [fake_doc])
    ctx = spc.load_strategic_planning_context()
    assert "Quality criteria" in ctx
    assert "7.1 Goals.md" in ctx
    # Sections not in the requested set should NOT appear
    assert "Unrelated content" not in ctx
