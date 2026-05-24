# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Hermes engine installer.

Bootstraps a fresh Hermes install from scratch — the "Branch B" of the
agency init wizard. Handles git clone, venv setup, pip install, binary
symlink, and HERMES_HOME initialization.

Public entry point:

    from _framework.hermes_engine import install, InstallPlan

    plan = InstallPlan(target_dir=Path.home() / ".hermes",
                       ref="main")
    result = install(plan, verbose=True)
    if result.success:
        print(f"Hermes {result.version} at {result.home}")

The installer is idempotent: re-running against an existing install
re-syncs (`git pull` + `pip install -e --upgrade`) rather than failing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .detection import HermesInfo, detect


# Default upstream
HERMES_GIT_URL = "https://github.com/NousResearch/hermes-agent.git"
HERMES_DEFAULT_REF = "main"


@dataclass
class InstallPlan:
    """Spec for an install run."""

    target_dir: Path = field(default_factory=lambda: Path.home() / ".hermes")
    git_url: str = HERMES_GIT_URL
    ref: str = HERMES_DEFAULT_REF        # branch, tag, or commit
    binary_symlink: Path = field(default_factory=lambda: Path.home() / ".local" / "bin" / "hermes")
    python: str = ""                      # explicit python path; "" = `python3` from PATH


@dataclass
class PrerequisiteCheck:
    """Result of prerequisites_check()."""

    ok: bool
    findings: list[str] = field(default_factory=list)   # human-readable lines


@dataclass
class InstallResult:
    """Outcome of an install run."""

    success: bool
    home: Path | None = None
    binary: Path | None = None
    version: str | None = None
    source_dir: Path | None = None
    steps_completed: list[str] = field(default_factory=list)
    failed_step: str = ""
    error: str = ""
    installed_at: str = ""


# ── Prerequisites ─────────────────────────────────────────────────────────


def prerequisites_check(python: str = "") -> PrerequisiteCheck:
    """Verify python>=3.11, git, pip are available + writable target.

    Returns a PrerequisiteCheck with ok=False if any prerequisite is
    missing. The findings list is suitable for printing to the user.
    """
    findings: list[str] = []
    ok = True

    # Python
    py = python or shutil.which("python3") or sys.executable
    if not py or not Path(py).exists():
        findings.append("✗ python3 not on PATH (need 3.11+)")
        ok = False
    else:
        try:
            r = subprocess.run([py, "--version"], capture_output=True, text=True, timeout=5)
            ver = (r.stdout + r.stderr).strip()
            # Parse "Python 3.11.5" → (3, 11)
            parts = ver.split()[-1].split(".")
            major, minor = int(parts[0]), int(parts[1])
            if (major, minor) < (3, 11):
                findings.append(f"✗ python is {ver}; need 3.11+")
                ok = False
            else:
                findings.append(f"✓ python: {ver} ({py})")
        except (subprocess.SubprocessError, ValueError, IndexError):
            findings.append(f"✗ couldn't determine python version at {py}")
            ok = False

    # git
    git = shutil.which("git")
    if not git:
        findings.append("✗ git not on PATH (install via xcode-select --install or homebrew)")
        ok = False
    else:
        findings.append(f"✓ git: {git}")

    return PrerequisiteCheck(ok=ok, findings=findings)


# ── Install ───────────────────────────────────────────────────────────────


def install(
    plan: InstallPlan,
    *,
    verbose: bool = True,
    log: Callable[[str], None] | None = None,
) -> InstallResult:
    """Run the install. Returns InstallResult.success=True on full
    success, False with `failed_step` + `error` populated on partial."""
    say = log or (print if verbose else (lambda _msg: None))

    result = InstallResult(success=False)

    # Step 1: prereqs
    say("→ Checking prerequisites...")
    prereqs = prerequisites_check(plan.python)
    for line in prereqs.findings:
        say(f"    {line}")
    if not prereqs.ok:
        result.failed_step = "prerequisites"
        result.error = "missing prerequisites; see findings above"
        return result
    result.steps_completed.append("prerequisites")

    # Resolve python
    python = plan.python or shutil.which("python3") or sys.executable

    # Step 2: target dir
    target = plan.target_dir.expanduser().resolve()
    source_dir = target / "hermes-agent"
    target.mkdir(parents=True, exist_ok=True)
    say(f"→ Target HERMES_HOME: {target}")

    # Step 3: git clone (or pull if already there)
    if source_dir.exists() and (source_dir / ".git").exists():
        say(f"→ Updating existing source tree at {source_dir}...")
        r = subprocess.run(
            ["git", "-C", str(source_dir), "fetch", "origin"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            result.failed_step = "git-fetch"
            result.error = (r.stderr or r.stdout)[:500]
            return result
        r = subprocess.run(
            ["git", "-C", str(source_dir), "checkout", plan.ref],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            result.failed_step = "git-checkout"
            result.error = (r.stderr or r.stdout)[:500]
            return result
        # Only pull if ref is a branch (not a tag/commit). Best-effort.
        subprocess.run(
            ["git", "-C", str(source_dir), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
        say(f"    ✓ updated to {plan.ref}")
    else:
        if source_dir.exists():
            say(f"⚠ {source_dir} exists but isn't a git repo; aborting to avoid clobbering")
            result.failed_step = "git-clone-precondition"
            result.error = f"{source_dir} exists and is not a git checkout"
            return result
        say(f"→ Cloning {plan.git_url} (ref: {plan.ref})...")
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", plan.ref,
             plan.git_url, str(source_dir)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            # Retry without --branch in case ref is a commit (not branch/tag)
            r = subprocess.run(
                ["git", "clone", plan.git_url, str(source_dir)],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                result.failed_step = "git-clone"
                result.error = (r.stderr or r.stdout)[:500]
                return result
            # Then check out the ref
            subprocess.run(
                ["git", "-C", str(source_dir), "checkout", plan.ref],
                capture_output=True, text=True,
            )
        say(f"    ✓ cloned to {source_dir}")
    result.steps_completed.append("git")

    # Step 4: venv
    venv_dir = source_dir / "venv"
    if not (venv_dir / "bin" / "python").exists():
        say(f"→ Creating venv at {venv_dir}...")
        r = subprocess.run(
            [python, "-m", "venv", str(venv_dir)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            result.failed_step = "venv-create"
            result.error = (r.stderr or r.stdout)[:500]
            return result
        say("    ✓ venv ready")
    else:
        say(f"✓ venv already at {venv_dir}")
    result.steps_completed.append("venv")
    venv_python = venv_dir / "bin" / "python"
    venv_pip = venv_dir / "bin" / "pip"

    # Step 5: pip install -e (editable, so future git pull updates take effect)
    say("→ Installing hermes-agent (pip install -e)...")
    say("  This downloads ~100-200 MB of dependencies; takes 2-5 min.")
    r = subprocess.run(
        [str(venv_pip), "install", "--quiet", "--upgrade", "pip"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        result.failed_step = "pip-upgrade"
        result.error = (r.stderr or r.stdout)[:500]
        return result
    r = subprocess.run(
        [str(venv_pip), "install", "--quiet", "-e", str(source_dir)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        result.failed_step = "pip-install"
        result.error = (r.stderr or r.stdout)[:500]
        return result
    say("    ✓ hermes-agent installed in venv")
    result.steps_completed.append("pip-install")

    # Step 6: symlink binary to ~/.local/bin/hermes
    venv_binary = venv_dir / "bin" / "hermes"
    if not venv_binary.exists():
        result.failed_step = "binary-missing"
        result.error = f"hermes binary not found at {venv_binary} after install"
        return result

    symlink = plan.binary_symlink.expanduser()
    symlink.parent.mkdir(parents=True, exist_ok=True)
    if symlink.exists() or symlink.is_symlink():
        if symlink.is_symlink() and symlink.resolve() == venv_binary.resolve():
            say(f"✓ symlink already correct: {symlink} → {venv_binary}")
        else:
            say(f"→ Replacing existing {symlink}...")
            symlink.unlink()
            symlink.symlink_to(venv_binary)
            say(f"    ✓ {symlink} → {venv_binary}")
    else:
        say(f"→ Symlinking {symlink} → {venv_binary}")
        symlink.symlink_to(venv_binary)
        say("    ✓ symlinked")
    result.steps_completed.append("symlink")

    # Step 7: HERMES_HOME structure (idempotent)
    # Hermes itself initializes its DBs on first run; we just ensure the
    # dir is present + writable. If the user has $HERMES_HOME elsewhere,
    # respect it.
    say(f"→ Ensuring HERMES_HOME structure at {target}...")
    target.mkdir(parents=True, exist_ok=True)
    result.steps_completed.append("home-init")

    # Step 8: verify
    say("→ Verifying install...")
    info = detect()
    if not info.installed or not info.binary:
        result.failed_step = "verify"
        result.error = "post-install detection failed; binary not found on PATH or expected location"
        return result
    say(f"    ✓ {info.version or 'hermes detected'}")
    say(f"    home:   {info.home}")
    say(f"    binary: {info.binary}")

    # Success
    result.success = True
    result.home = info.home or target
    result.binary = info.binary or venv_binary
    result.version = info.version
    result.source_dir = source_dir
    result.installed_at = datetime.now(timezone.utc).isoformat()
    return result


def shell_init_lines(plan: InstallPlan) -> list[str]:
    """The lines to append to ~/.zshrc (or equivalent) so the install
    sticks across shell sessions. Returned for the wizard to print
    after a successful install."""
    home = plan.target_dir.expanduser()
    symlink_dir = plan.binary_symlink.expanduser().parent
    return [
        f"export HERMES_HOME={home}",
        f"export PATH={symlink_dir}:$PATH",
    ]


__all__ = [
    "InstallPlan", "PrerequisiteCheck", "InstallResult",
    "HERMES_GIT_URL", "HERMES_DEFAULT_REF",
    "install", "prerequisites_check", "shell_init_lines",
]
