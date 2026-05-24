"""Control panel sanity test — the app builds and the data endpoint returns JSON."""

from __future__ import annotations

import json

import pytest


@pytest.mark.seam
def test_panel_app_builds():
    from _framework.ops.control_panel import build_app
    app = build_app()
    routes = [r for r in app.router.routes()]
    paths = {r.resource.canonical for r in routes if r.resource}
    assert "/control-panel" in paths
    assert "/control-panel/data" in paths


@pytest.mark.seam
def test_panel_data_returns_dict(tmp_agency):
    """The data fetcher should always return a dict shape, even on an
    empty deployment (no learning.db yet, no profiles)."""
    from _framework.ops.control_panel import (
        _learning_health,
        _profiles_overview,
        _manifest_state,
        _recent_events,
    )
    learning = _learning_health()
    profiles = _profiles_overview()
    manifest = _manifest_state()
    events = _recent_events(50)
    assert isinstance(learning, dict)
    assert "rules_total" in learning
    assert isinstance(profiles, list)
    assert isinstance(manifest, dict)
    assert isinstance(events, list)


@pytest.mark.seam
def test_panel_data_after_capture(tmp_agency):
    """After capturing a rule, the panel data reflects it."""
    from _framework.learning import capture_correction
    from _framework.ops.control_panel import _learning_health

    capture_correction(
        correction="A correction for panel testing.",
        source="cli:panel-test",
        skill_tags=["draft-composer"],
    )
    health = _learning_health()
    assert health["rules_total"] >= 1
    assert health["available"] is True
