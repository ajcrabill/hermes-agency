# SEAM TEST — owned by HermesAgency.
"""
agency_docs loader (§1.1 always-loaded background) — six tests.

Verifies the v0.22.4-spec aim-vs-brake split is implementation-true:
  - Goals.md / Personal.md / Work.md / Clients.md / SOUL.md are
    loaded into the pre_llm_call context block.
  - Guardrails.md is NOT loaded by this path (enforcement-layer
    concern; loaded by Sentinel/send-guard/audit instead).
  - The block has the right header signaling aim-vs-brake.
  - Missing files don't crash; the loader returns empty string
    when nothing is present.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_agency_home(tmp_path, monkeypatch):
    """Point AGENCY_HOME at a tmp dir so this test is hermetic."""
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path))
    # constants.py reads AGENCY_HOME at import time; force re-import
    import importlib
    import _framework.constants
    importlib.reload(_framework.constants)
    import _framework.agency_docs.loader
    importlib.reload(_framework.agency_docs.loader)
    yield


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_load_agency_context_empty_when_no_docs():
    from _framework.agency_docs import load_agency_context

    assert load_agency_context(profile="loriah") == ""


def test_load_agency_context_includes_goals(tmp_path):
    from _framework.agency_docs import load_agency_context
    from _framework.constants import GOALS_MD

    _write(GOALS_MD, "# Goals\n\nOutcome 1: foo")
    block = load_agency_context(profile="loriah")
    assert "Goals" in block
    assert "Outcome 1: foo" in block


def test_load_agency_context_includes_all_aim_docs(tmp_path):
    from _framework.agency_docs import load_agency_context
    from _framework.constants import GOALS_MD, PERSONAL_MD, WORK_MD, CLIENTS_MD

    _write(GOALS_MD, "GOALS_CONTENT")
    _write(PERSONAL_MD, "PERSONAL_CONTENT")
    _write(WORK_MD, "WORK_CONTENT")
    _write(CLIENTS_MD, "CLIENTS_CONTENT")

    block = load_agency_context(profile="loriah")
    assert "GOALS_CONTENT" in block
    assert "PERSONAL_CONTENT" in block
    assert "WORK_CONTENT" in block
    assert "CLIENTS_CONTENT" in block


def test_load_agency_context_omits_guardrails(tmp_path):
    """Critical: Guardrails.md is intentionally NOT in the always-loaded block.

    Per v0.22.4-spec aim/brake split — Guardrails are enforcement-layer
    only (Sentinel, send-guard, audit), never always-on prompt context.
    """
    from _framework.agency_docs import load_agency_context
    from _framework.constants import GOALS_MD, GUARDRAILS_MD

    _write(GOALS_MD, "GOALS_CONTENT")
    _write(GUARDRAILS_MD, "PROHIBITED_GUARDRAIL_CONTENT_SHOULD_NOT_APPEAR")

    block = load_agency_context(profile="loriah")
    assert "GOALS_CONTENT" in block
    assert "PROHIBITED_GUARDRAIL_CONTENT_SHOULD_NOT_APPEAR" not in block


def test_load_agency_context_includes_profile_soul(tmp_path):
    from _framework.agency_docs import load_agency_context
    from _framework.constants import AGENCY_HOME

    _write(AGENCY_HOME / "profiles" / "devon" / "SOUL.md", "DEVON_SOUL_CONTENT")
    block = load_agency_context(profile="devon")
    assert "DEVON_SOUL_CONTENT" in block
    assert "devon" in block.lower()


def test_load_agency_context_header_names_aim_vs_brake(tmp_path):
    """The block's header must establish that this is aim, not brake."""
    from _framework.agency_docs import load_agency_context
    from _framework.constants import GOALS_MD

    _write(GOALS_MD, "GOALS_CONTENT")
    block = load_agency_context(profile="loriah")
    assert "always-loaded background" in block.lower()
    # Should mention that Guardrails are checked separately at enforcement
    assert "guardrail" in block.lower()
