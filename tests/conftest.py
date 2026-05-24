"""Shared pytest fixtures across HermesAgency's test suite."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest


# Make sure the framework is importable in tests without installation.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def tmp_agency(monkeypatch, tmp_path) -> Path:
    """
    Provision a fresh deployment skeleton at a temporary AGENCY_HOME for a
    single test. The fixture sets AGENCY_HOME via env var BEFORE the
    framework modules read it.
    """
    agency = tmp_path / ".agency"
    agency.mkdir()
    (agency / "_state").mkdir()
    (agency / "_health" / "audits").mkdir(parents=True)
    (agency / "profiles").mkdir()
    (agency / "framework-vault").mkdir()
    monkeypatch.setenv("AGENCY_HOME", str(agency))

    # The constants module caches the path at import time. Tests that
    # want the override to take effect must import (or reimport) the
    # framework modules AFTER this fixture has run.
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]
    return agency


@pytest.fixture
def write_manifest(tmp_agency):
    """Helper: write a manifest YAML body into the temp deployment."""

    def _write(body: str) -> Path:
        path = tmp_agency / "deployment.yaml"
        path.write_text(body)
        return path

    return _write
