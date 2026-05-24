# SEAM TEST — owned by HermesAgency.
"""
Guardrails.md loader + enforcement-layer wiring (v0.23.1).

Eight tests:
  1. load_guardrails returns empty when no file
  2. load_guardrails returns content when present
  3. load_guardrails falls back to Values.md (legacy)
  4. load_guardrails_parsed extracts Guardrail + Interim Guardrails
  5. load_guardrails_parsed extracts Initiative refs (skill/script paths)
  6. Sentinel guardrails_watch focuses on Interim Guardrails
     (the SMART layer), not on Guardrail value statements
  7. Sentinel emits warning when Interim Guardrails lack
     Initiative refs (unresourced)
  8. send_guard.evaluate notes Interim Guardrail count when Guardrails.md
     is present
"""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def isolated_agency_home(tmp_path, monkeypatch):
    """Point AGENCY_HOME at a tmp dir so this test is hermetic.

    Matches the conftest `tmp_agency` fixture pattern: env var first,
    then purge any cached `_framework.*` modules so re-imports pick
    up the new path. Teardown purges again so the next test is clean.
    """
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path))
    # See conftest.py::tmp_agency — also set HERMES_AGENCY_STATE so
    # _resolve_state_root() doesn't escape into the real ~/.hermes/.
    monkeypatch.setenv("HERMES_AGENCY_STATE", str(tmp_path / "_state"))
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]
    yield
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]


def _write_guardrails(body: str) -> None:
    from _framework.constants import GUARDRAILS_MD
    GUARDRAILS_MD.parent.mkdir(parents=True, exist_ok=True)
    GUARDRAILS_MD.write_text(body, encoding="utf-8")


def _write_values_legacy(body: str) -> None:
    from _framework.constants import VALUES_MD
    VALUES_MD.parent.mkdir(parents=True, exist_ok=True)
    VALUES_MD.write_text(body, encoding="utf-8")


def test_load_guardrails_empty_when_no_file():
    from _framework.guardrails_loader import load_guardrails
    assert load_guardrails() == ""


def test_load_guardrails_returns_content():
    from _framework.guardrails_loader import load_guardrails
    _write_guardrails("# Guardrails\n\nSome content here.")
    assert "Some content here." in load_guardrails()


def test_load_guardrails_falls_back_to_values_md():
    """v0.22.4-spec rename is transitional; legacy Values.md must
    still work until v0.24."""
    from _framework.guardrails_loader import load_guardrails
    _write_values_legacy("# Values (legacy)\n\nLegacy content.")
    assert "Legacy content." in load_guardrails()


def test_load_guardrails_parsed_extracts_structure():
    from _framework.guardrails_loader import load_guardrails_parsed
    _write_guardrails(
        """# Guardrails

### Guardrail 1 — Work the Principal is proud of

The business will not pursue clients whose work would be a poor fit.

**Interim Guardrail 1.1 — Engagement fit screen**

The percentage of new coaching engagements that pass the documented values-fit screen before contracting will increase from 0% in February 2026 to 100% by March 2026, measured monthly.

Initiatives serving Interim Guardrail 1.1:
- skill: `cos/values-fit-screen-prepper` *(agentic)*
"""
    )
    parsed = load_guardrails_parsed()
    assert parsed is not None
    assert len(parsed["guardrails"]) == 1
    g = parsed["guardrails"][0]
    assert "proud of" in g["title"]
    assert len(g["interim_guardrails"]) == 1
    ig = g["interim_guardrails"][0]
    assert "fit screen" in ig["title"].lower()


def test_load_guardrails_parsed_extracts_initiative_refs():
    from _framework.guardrails_loader import load_guardrails_parsed
    _write_guardrails(
        """# Guardrails

### Guardrail 1 — Honesty

The business will not misrepresent.

**Interim Guardrail 1.1 — Honesty checks**

100% of outbound communications pass the honesty self-check.

Initiatives:
- skill: `cos/honesty-self-check` *(agentic)*
- script: `cos/outbound-honesty-scanner.py` *(deterministic)*
"""
    )
    parsed = load_guardrails_parsed()
    refs = parsed["guardrails"][0]["interim_guardrails"][0]["initiative_refs"]
    assert "cos/honesty-self-check" in refs
    assert "cos/outbound-honesty-scanner.py" in refs


def test_sentinel_guardrails_watch_focuses_on_interim_guardrails():
    """Critical: Sentinel observes the SMART, measurable layer
    (Interim Guardrails), not the value statements (Guardrails)."""
    _write_guardrails(
        """# Guardrails

### Guardrail 1 — Honesty

A value statement, not measurable.

**Interim Guardrail 1.1 — Honesty checks**

100% of outbound passes honesty check.

- skill: `cos/honesty-self-check`

**Interim Guardrail 1.2 — Public-content review**

100% of public posts pass values-fit screen.

- skill: `cos/public-content-reviewer`
"""
    )
    from _framework.sentinel.monitors import guardrails_watch
    result = guardrails_watch()
    assert result["interim_guardrails_tracked"] == 2
    assert result["guardrails_in_scope"] == 1
    # No unresourced interims — every one has at least one Initiative
    assert result["interim_without_initiatives"] == 0


def test_sentinel_flags_unresourced_interim_guardrails():
    """An Interim Guardrail with no Initiative refs is a warning:
    nothing is producing the artifact that would move the metric."""
    _write_guardrails(
        """# Guardrails

### Guardrail 1 — Honesty

Value statement.

**Interim Guardrail 1.1 — Honesty check rate**

100% of outbound passes honesty check.

(no initiatives listed)
"""
    )
    from _framework.sentinel.monitors import guardrails_watch
    result = guardrails_watch()
    assert result["interim_guardrails_tracked"] == 1
    assert result["interim_without_initiatives"] == 1


def test_send_guard_evaluate_notes_interim_guardrail_count():
    """send_guard.evaluate should note Interim Guardrail count
    in the decision reasons when Guardrails.md is present."""
    _write_guardrails(
        """# Guardrails

### Guardrail 1 — Honesty

Value statement.

**Interim Guardrail 1.1 — Check rate**

100% by March 2026.

- skill: `cos/honesty-check`

**Interim Guardrail 1.2 — Review rate**

90% by April 2026.

- skill: `cos/public-content-reviewer`
"""
    )
    from _framework.send_guard.send_guard import (
        SendCandidate,
        evaluate,
        Verdict,
    )

    candidate = SendCandidate(
        to=["recipient@example.com"],
        from_addr="me@example.com",
        subject="Hi",
        body="Test message",
        skill="test-skill",
        profile="cos",
    )
    decision = evaluate(candidate)
    # Reason text should reference Interim Guardrails specifically
    joined = " ".join(decision.reasons).lower()
    assert "interim guardrail" in joined
    assert "2" in joined  # the count
