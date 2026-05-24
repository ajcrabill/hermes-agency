"""Seam tests for the v0.20 state-collapse migration."""

from __future__ import annotations

import pytest


def _setup_env(tmp_path, monkeypatch, with_hermes_home: bool = True):
    """Set up HOME/AGENCY_HOME/HERMES_HOME pointing at tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    if with_hermes_home:
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    else:
        monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("HERMES_AGENCY_STATE", raising=False)
    # Clear cached module state
    import sys
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]


def test_plan_when_no_legacy_state(tmp_path, monkeypatch):
    """Fresh install — no legacy state, no migration needed."""
    _setup_env(tmp_path, monkeypatch)
    from _framework.migration import plan_state_collapse
    plan = plan_state_collapse()
    assert plan.nothing_to_migrate is True


def test_plan_detects_legacy_state(tmp_path, monkeypatch):
    """Legacy ~/.agency/_state/ exists with files — plan lists them."""
    _setup_env(tmp_path, monkeypatch)
    legacy = tmp_path / ".agency" / "_state"
    legacy.mkdir(parents=True)
    (legacy / "learning.db").write_text("fake learning db")
    (legacy / "autonomy.db").write_text("fake autonomy db")

    from _framework.migration import plan_state_collapse
    plan = plan_state_collapse()
    assert plan.nothing_to_migrate is False
    assert plan.already_migrated is False
    assert len(plan.files_to_move) == 2
    file_names = {p.name for p in plan.files_to_move}
    assert file_names == {"learning.db", "autonomy.db"}


def test_plan_detects_already_migrated(tmp_path, monkeypatch):
    """v0.20+ location has files, legacy is empty — already migrated."""
    _setup_env(tmp_path, monkeypatch)
    target = tmp_path / ".hermes" / "agency-state"
    target.mkdir(parents=True)
    (target / "learning.db").write_text("v0.20+ learning db")

    from _framework.migration import plan_state_collapse
    plan = plan_state_collapse()
    assert plan.already_migrated is True


def test_apply_moves_legacy_state_to_v020(tmp_path, monkeypatch):
    """Files at legacy location get moved to v0.20+ location."""
    _setup_env(tmp_path, monkeypatch)
    legacy_state = tmp_path / ".agency" / "_state"
    legacy_state.mkdir(parents=True)
    (legacy_state / "learning.db").write_text("learning")
    (legacy_state / "events.db").write_text("events")

    legacy_health = tmp_path / ".agency" / "_health"
    legacy_health.mkdir(parents=True)
    (legacy_health / "operator-actions.jsonl").write_text("{}")

    from _framework.migration import plan_state_collapse, apply_state_collapse
    plan = plan_state_collapse()
    result = apply_state_collapse(plan)

    assert result.success is True
    assert len(result.moved) == 3

    target_state = tmp_path / ".hermes" / "agency-state"
    target_health = target_state / "_health"
    assert (target_state / "learning.db").exists()
    assert (target_state / "learning.db").read_text() == "learning"
    assert (target_state / "events.db").exists()
    assert (target_health / "operator-actions.jsonl").exists()

    # Tombstone written
    tombstone = tmp_path / ".agency" / "_state.MIGRATED-TO-v0.20"
    assert tombstone.exists()


def test_apply_is_idempotent(tmp_path, monkeypatch):
    """Re-applying after success is a no-op."""
    _setup_env(tmp_path, monkeypatch)
    legacy = tmp_path / ".agency" / "_state"
    legacy.mkdir(parents=True)
    (legacy / "learning.db").write_text("x")

    from _framework.migration import plan_state_collapse, apply_state_collapse

    # First apply
    result1 = apply_state_collapse(plan_state_collapse())
    assert result1.success is True
    assert len(result1.moved) == 1

    # Second apply — already migrated
    plan2 = plan_state_collapse()
    assert plan2.already_migrated is True
    result2 = apply_state_collapse(plan2)
    assert result2.success is True
    assert len(result2.moved) == 0


def test_constants_resolve_to_v020_when_hermes_exists(tmp_path, monkeypatch):
    """STATE_DIR resolves to ~/.hermes/agency-state/ when ~/.hermes/
    + ~/.hermes/agency-state/ exists."""
    _setup_env(tmp_path, monkeypatch)
    (tmp_path / ".hermes").mkdir()
    (tmp_path / ".hermes" / "agency-state").mkdir()

    from _framework.constants import STATE_DIR
    assert "agency-state" in str(STATE_DIR)
    assert ".agency/_state" not in str(STATE_DIR)


def test_constants_honor_explicit_env_override(tmp_path, monkeypatch):
    """$HERMES_AGENCY_STATE wins over auto-detection."""
    custom = tmp_path / "custom-state-location"
    custom.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    monkeypatch.setenv("HERMES_AGENCY_STATE", str(custom))
    import sys
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]

    from _framework.constants import STATE_DIR
    assert STATE_DIR == custom
