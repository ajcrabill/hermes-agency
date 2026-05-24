# SEAM TEST — owned by HermesAgency.
"""
Strategic-alignment audit rules (v0.23.3) + findings-only-semantics.

Verifies the six new audit rules:
  - unaligned-skills
  - unaligned-initiatives
  - unaligned-interim-goals
  - stale-skill-status
  - abandoned-outcome
  - agency-context-injection

Plus the load-bearing constraint: **the audit never writes to the
vault filesystem**. Findings only, never mutations.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_agency_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_AGENCY_STATE", str(tmp_path / "_state"))
    # Set up minimal deployment skeleton so audit_deployment() works
    (tmp_path / "_state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "profiles").mkdir(parents=True, exist_ok=True)
    (tmp_path / "agency-vault").mkdir(parents=True, exist_ok=True)
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]
    yield
    for mod in [m for m in list(sys.modules) if m.startswith("_framework")]:
        del sys.modules[mod]


def _make_strategic_skill(tmp_path: Path, profile: str, skill: str, frontmatter: dict) -> Path:
    """Write a SKILL.md with the given frontmatter under tmp_path/profiles/<p>/skills/<s>/."""
    skill_dir = tmp_path / "profiles" / profile / "skills" / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append("# Skill body")
    (skill_dir / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
    return skill_dir / "SKILL.md"


# ── findings-only / never-mutation invariant ─────────────────────


def _snapshot_files(root: Path) -> dict[Path, tuple[int, float]]:
    """Capture (size, mtime) for every file under root."""
    snap: dict[Path, tuple[int, float]] = {}
    for p in root.rglob("*"):
        if p.is_file():
            stat = p.stat()
            snap[p] = (stat.st_size, stat.st_mtime)
    return snap


def test_audit_produces_findings_never_mutations_to_vault(tmp_path):
    """Critical: the audit run never writes to the vault filesystem.

    Per StrategicPlanning.md §7.5 and v0.22.12-spec acceptance #3:
    "All six new audit rules produce findings, never mutations."

    Scope: vault filesystem (Goals.md / Guardrails.md / SKILL.md /
    profiles / etc.) and the framework code. State DBs may
    initialize themselves on first read (SQLite default behavior);
    that's not what this invariant guards against.
    """
    from _framework.audit import audit_alignment

    # Set up a deployment with some skills + Goals.md
    _make_strategic_skill(tmp_path, "loriah", "weekly-review", {
        "skill_id": "weekly-review",
        "interim_goal": "G1.1",
        # missing outcome, outcome_metric, status — rule should fire
    })
    (tmp_path / "agency-vault" / "Goals.md").write_text(
        "# Goals\n\nOutcome 1.\n", encoding="utf-8"
    )
    (tmp_path / "agency-vault" / "Personal.md").write_text(
        "# Personal\n", encoding="utf-8"
    )

    # Snapshot the VAULT before (agency-vault + profiles, not _state)
    def vault_snapshot() -> dict[Path, tuple[int, float]]:
        snap: dict[Path, tuple[int, float]] = {}
        for root_dir in (tmp_path / "agency-vault", tmp_path / "profiles"):
            if not root_dir.exists():
                continue
            for p in root_dir.rglob("*"):
                if p.is_file():
                    stat = p.stat()
                    snap[p] = (stat.st_size, stat.st_mtime)
        return snap

    before = vault_snapshot()

    # Run the audit (full deployment)
    report = audit_alignment.audit_deployment()

    after = vault_snapshot()

    # No vault file created, removed, or modified
    assert set(before.keys()) == set(after.keys()), (
        "audit added or removed files in the vault — must be findings-only"
    )
    for p, (size, mtime) in before.items():
        assert after[p] == (size, mtime), (
            f"audit modified vault file {p} — must be findings-only"
        )

    # And the audit did produce findings (the deployment IS incomplete)
    finding_codes = {f.code for f in report.findings}
    assert "unaligned-skills" in finding_codes or "agency-context-injection" in finding_codes


# ── unaligned-skills ─────────────────────────────────────────────


def test_unaligned_skills_fires_on_strategic_skill_missing_required_keys(tmp_path):
    from _framework.audit import audit_alignment

    _make_strategic_skill(tmp_path, "loriah", "incomplete-skill", {
        "skill_id": "incomplete-skill",
        "interim_goal": "G1.1",
        # missing outcome, outcome_metric, alignment_argument, status
    })
    report = audit_alignment.audit_skill(skill="incomplete-skill", profile="loriah")
    codes = [f.code for f in report.findings]
    # Should fire 4 unaligned-skills findings (one per missing key)
    assert codes.count("unaligned-skills") >= 4


def test_unaligned_skills_silent_on_utility_skill(tmp_path):
    """Skills without `interim_goal` are utility work; this rule
    shouldn't fire on them."""
    from _framework.audit import audit_alignment

    _make_strategic_skill(tmp_path, "loriah", "utility-skill", {
        "skill_id": "utility-skill",
        # No interim_goal => utility skill, rule skips
    })
    report = audit_alignment.audit_skill(skill="utility-skill", profile="loriah")
    codes = [f.code for f in report.findings]
    assert "unaligned-skills" not in codes


def test_unaligned_skills_flags_invalid_status_color(tmp_path):
    from _framework.audit import audit_alignment

    _make_strategic_skill(tmp_path, "loriah", "bad-status", {
        "skill_id": "bad-status",
        "interim_goal": "G1.1",
        "outcome": "O1",
        "outcome_metric": "metric",
        "alignment_argument": "arg",
        "status": "purple",  # not a valid color
    })
    report = audit_alignment.audit_skill(skill="bad-status", profile="loriah")
    messages = " ".join(f.message for f in report.findings)
    assert "invalid status" in messages
    assert "purple" in messages


# ── unaligned-initiatives ────────────────────────────────────────


def test_unaligned_initiatives_fires_when_outcome_without_interim_goal(tmp_path):
    """Strategic skills must connect through Interim Goals; declaring
    an outcome without the bridge is incomplete."""
    from _framework.audit import audit_alignment

    _make_strategic_skill(tmp_path, "loriah", "no-bridge", {
        "skill_id": "no-bridge",
        "outcome": "O1",
        # outcome declared but interim_goal missing
    })
    report = audit_alignment.audit_skill(skill="no-bridge", profile="loriah")
    codes = [f.code for f in report.findings]
    assert "unaligned-initiatives" in codes


# ── unaligned-interim-goals ──────────────────────────────────────


def test_unaligned_interim_goals_fires_when_goals_md_absent(tmp_path):
    from _framework.audit import audit_alignment

    # No Goals.md in tmp_path
    report = audit_alignment.audit_deployment()
    codes = [f.code for f in report.findings]
    assert "unaligned-interim-goals" in codes


def test_unaligned_interim_goals_silent_when_goals_md_present(tmp_path):
    from _framework.audit import audit_alignment

    (tmp_path / "agency-vault" / "Goals.md").write_text(
        "# Goals\n\nOutcome 1.\n", encoding="utf-8"
    )
    report = audit_alignment.audit_deployment()
    codes = [f.code for f in report.findings]
    # v0.23.3 only checks file existence; deeper checks land in v0.23.4
    assert "unaligned-interim-goals" not in codes


# ── stale-skill-status ───────────────────────────────────────────


def test_stale_skill_status_fires_on_red_yellow_older_than_4_weeks(tmp_path):
    from _framework.audit import audit_alignment

    path = _make_strategic_skill(tmp_path, "loriah", "old-yellow", {
        "skill_id": "old-yellow",
        "interim_goal": "G1.1",
        "outcome": "O1",
        "outcome_metric": "m",
        "alignment_argument": "a",
        "status": "yellow",
    })
    # Set mtime to 35 days ago
    thirty_five_days_ago = time.time() - (35 * 24 * 3600)
    os.utime(path, (thirty_five_days_ago, thirty_five_days_ago))

    report = audit_alignment.audit_skill(skill="old-yellow", profile="loriah")
    codes = [f.code for f in report.findings]
    assert "stale-skill-status" in codes


def test_stale_skill_status_silent_on_green(tmp_path):
    from _framework.audit import audit_alignment

    path = _make_strategic_skill(tmp_path, "loriah", "old-green", {
        "skill_id": "old-green",
        "interim_goal": "G1.1",
        "outcome": "O1",
        "outcome_metric": "m",
        "alignment_argument": "a",
        "status": "green",
    })
    # Old but Green — rule should not fire
    thirty_five_days_ago = time.time() - (35 * 24 * 3600)
    os.utime(path, (thirty_five_days_ago, thirty_five_days_ago))

    report = audit_alignment.audit_skill(skill="old-green", profile="loriah")
    codes = [f.code for f in report.findings]
    assert "stale-skill-status" not in codes


# ── abandoned-outcome ────────────────────────────────────────────


def test_abandoned_outcome_fires_when_no_skills_declare_outcome(tmp_path):
    from _framework.audit import audit_alignment

    # Profile exists, but no skills have outcome: frontmatter
    (tmp_path / "profiles" / "loriah").mkdir(parents=True, exist_ok=True)
    report = audit_alignment.audit_deployment()
    codes = [f.code for f in report.findings]
    assert "abandoned-outcome" in codes


def test_abandoned_outcome_silent_when_skills_cover_outcomes(tmp_path):
    from _framework.audit import audit_alignment

    _make_strategic_skill(tmp_path, "loriah", "covered", {
        "skill_id": "covered",
        "interim_goal": "G1.1",
        "outcome": "O1",
        "outcome_metric": "m",
        "alignment_argument": "a",
        "status": "green",
    })
    report = audit_alignment.audit_deployment()
    codes = [f.code for f in report.findings]
    assert "abandoned-outcome" not in codes


# ── agency-context-injection ─────────────────────────────────────


def test_agency_context_injection_fires_when_aim_docs_missing(tmp_path):
    from _framework.audit import audit_alignment

    # Nothing under agency-vault
    report = audit_alignment.audit_deployment()
    codes = [f.code for f in report.findings]
    assert "agency-context-injection" in codes


def test_agency_context_injection_silent_when_all_present(tmp_path):
    from _framework.audit import audit_alignment

    for name in ("Goals.md", "Personal.md", "Work.md", "Clients.md", "Guardrails.md"):
        (tmp_path / "agency-vault" / name).write_text("# stub\n", encoding="utf-8")
    report = audit_alignment.audit_deployment()
    codes = [f.code for f in report.findings]
    assert "agency-context-injection" not in codes
