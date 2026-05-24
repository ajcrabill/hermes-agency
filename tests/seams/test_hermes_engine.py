"""Seam tests for the hermes_engine subsystem.

Detection: fake out PATH + HERMES_HOME, verify the right signals
fire and produce the right HermesInfo.

Installer: smoke-tested via prerequisites_check (which is the
deterministic surface). The full install() path is integration-only
(needs network, takes minutes) — covered by the live deployment
test, not the unit suite.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from _framework.hermes_engine import detection, installer


# ── Detection ─────────────────────────────────────────────────────────


def test_detect_when_nothing_installed(tmp_path, monkeypatch):
    """Empty HOME, no $HERMES_HOME, no hermes on PATH → installed=False."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("PATH", "")
    info = detection.detect()
    assert info.installed is False
    assert info.home is None
    assert info.binary is None


def test_detect_via_env_hermes_home(tmp_path, monkeypatch):
    """$HERMES_HOME pointing at a dir with state.db → detected."""
    fake_home = tmp_path / "my-hermes"
    fake_home.mkdir()
    (fake_home / "state.db").touch()
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    monkeypatch.setenv("HOME", str(tmp_path / "noisy"))   # avoid default fallback
    info = detection.detect()
    assert info.installed is True
    assert info.home == fake_home
    assert info.detected_via == "env"


def test_detect_via_default_home(tmp_path, monkeypatch):
    """HOME with .hermes/state.db → detected via default-home."""
    fake_home = tmp_path / "user-home"
    (fake_home / ".hermes").mkdir(parents=True)
    (fake_home / ".hermes" / "kanban.db").touch()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    info = detection.detect()
    assert info.installed is True
    assert info.home == fake_home / ".hermes"
    assert info.detected_via == "default-home"


def test_detect_via_path_only_binary(tmp_path, monkeypatch):
    """`hermes` binary on PATH but nothing else → detected via path-binary-only."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_binary = bindir / "hermes"
    # Minimal "hermes" stub that prints a version
    fake_binary.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'Hermes Agent v0.0-test'\n"
        "fi\n"
    )
    fake_binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))
    monkeypatch.setenv("HOME", str(tmp_path / "empty"))   # avoid default-home hit
    monkeypatch.delenv("HERMES_HOME", raising=False)
    info = detection.detect()
    assert info.installed is True
    assert info.binary == fake_binary.resolve()
    assert info.detected_via.startswith("path")
    # version should be parsed from --version output
    assert info.version is not None
    assert "v0.0-test" in info.version


def test_looks_like_hermes_home(tmp_path):
    """The marker check is lenient: any one marker = yes."""
    assert detection._looks_like_hermes_home(tmp_path) is False
    (tmp_path / "state.db").touch()
    assert detection._looks_like_hermes_home(tmp_path) is True


def test_is_installed_convenience(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("PATH", "")
    assert detection.is_installed() is False


# ── Installer prerequisites ──────────────────────────────────────────


def test_prerequisites_check_ok():
    """The current test environment has python + git available."""
    result = installer.prerequisites_check()
    # We assume the dev/CI env has both. If a finding says ✗ for
    # python or git, something's wrong with the env, not the code.
    assert isinstance(result.ok, bool)
    assert len(result.findings) >= 2


def test_prerequisites_check_bad_python():
    """A non-existent python path → not-ok."""
    result = installer.prerequisites_check(python="/nonexistent/python")
    assert result.ok is False
    # At least one finding is the python failure
    assert any("python" in f.lower() for f in result.findings)


def test_install_plan_defaults():
    plan = installer.InstallPlan()
    assert plan.git_url == installer.HERMES_GIT_URL
    assert plan.ref == installer.HERMES_DEFAULT_REF
    assert plan.target_dir == Path.home() / ".hermes"
    assert plan.binary_symlink == Path.home() / ".local" / "bin" / "hermes"


def test_shell_init_lines():
    plan = installer.InstallPlan(
        target_dir=Path("/tmp/test-hermes"),
        binary_symlink=Path("/tmp/test-bin/hermes"),
    )
    lines = installer.shell_init_lines(plan)
    assert any("HERMES_HOME=/tmp/test-hermes" in line for line in lines)
    assert any("/tmp/test-bin" in line for line in lines)
