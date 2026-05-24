"""Hermes-patch tests — idempotency, anchor detection, marker check."""

from __future__ import annotations

from pathlib import Path

import pytest


# Stub Hermes skill_commands.py — minimal but contains the anchor
_STUB_SKILL_COMMANDS = '''"""Stub of Hermes' skill_commands.py for testing the injection patch."""

from typing import Any
from pathlib import Path


def _inject_skill_config(loaded_skill, parts):
    """Placeholder."""
    pass


def _build_skill_message(
    loaded_skill: dict,
    skill_dir: Path | None,
    activation_note: str,
) -> str:
    content = str(loaded_skill.get("content") or "")
    parts = [activation_note, "", content.strip()]

    if skill_dir:
        parts.append("")
        parts.append(f"[Skill directory: {skill_dir}]")

    _inject_skill_config(loaded_skill, parts)

    return "\\n".join(parts)
'''


def _stub_hermes_install(tmp_agency, monkeypatch):
    """Create a stub Hermes install structure under tmp_agency."""
    hermes_home = tmp_agency.parent / ".hermes-test"
    hermes_agent = hermes_home / "hermes-agent" / "agent"
    hermes_agent.mkdir(parents=True)
    skill_commands = hermes_agent / "skill_commands.py"
    skill_commands.write_text(_STUB_SKILL_COMMANDS)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    return skill_commands


# v0.17 NOTE: the three tests below validated the text-anchor patch
# system used through v0.16. That system was retired in v0.17 when the
# framework pivoted to Hermes' documented plugin API
# (`hermes_agency_plugin/`). The REGISTRY is now empty by design;
# `skill_load_injection.py` remains as a deprecated module that no
# longer self-registers. These tests skip until v0.18 when the
# deprecated module is deleted entirely.
_PATCH_DEPRECATED_SKIP = pytest.mark.skip(
    reason="Text-anchor patches deprecated in v0.17 — replaced by "
           "Hermes plugin API hooks (hermes_agency_plugin/). "
           "Tests deleted along with the module in v0.18."
)


@pytest.mark.seam
@_PATCH_DEPRECATED_SKIP
def test_patch_detects_unapplied(tmp_agency, monkeypatch):
    _stub_hermes_install(tmp_agency, monkeypatch)
    from _framework.hermes_patches import check_status
    statuses = check_status()
    by_id = {s.id: s for s in statuses}
    assert by_id["skill_load_injection"].status == "unapplied"


@pytest.mark.seam
@_PATCH_DEPRECATED_SKIP
def test_patch_applies_idempotently(tmp_agency, monkeypatch):
    target = _stub_hermes_install(tmp_agency, monkeypatch)
    from _framework.hermes_patches import apply_all, check_status

    apply_all()
    statuses = check_status()
    by_id = {s.id: s for s in statuses}
    assert by_id["skill_load_injection"].status == "applied"

    # Marker should be present in the patched file
    text = target.read_text(encoding="utf-8")
    assert "HERMES_AGENCY_PATCH:skill_load_injection" in text
    assert "inject_for_skill" in text

    # Second apply should be a no-op
    apply_all()
    statuses = check_status()
    by_id = {s.id: s for s in statuses}
    assert by_id["skill_load_injection"].status == "applied"


@pytest.mark.seam
@_PATCH_DEPRECATED_SKIP
def test_patch_detects_anchor_missing(tmp_agency, monkeypatch):
    # Stub with the anchor removed
    hermes_home = tmp_agency.parent / ".hermes-noanchor"
    hermes_agent = hermes_home / "hermes-agent" / "agent"
    hermes_agent.mkdir(parents=True)
    (hermes_agent / "skill_commands.py").write_text(
        "# Hermes skill_commands.py without the anchor function call\n"
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    from _framework.hermes_patches import check_status
    statuses = check_status()
    by_id = {s.id: s for s in statuses}
    assert by_id["skill_load_injection"].status == "anchor-missing"
