# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment;
# customizations belong in ~/.agency/profiles/<P>/ or deployment.yaml.
"""
Brand-agnostic path constants.

Every path in the framework derives from these. Operators set
`AGENCY_HOME` (default `~/.agency`); the framework derives every other
path from it. No literal owner names, mail addresses, or deployment-
specific strings appear anywhere in `_framework/`.

This is the file the audit (§10.3) checks for vendor leaks and
deployment-specific values. Keep it data only.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Framework install location ────────────────────────────────────────────
# The directory containing this file (`_framework/`). Used to locate
# templates, scaffolds, and audit invariants relative to the framework
# install, regardless of where the deployment lives.
FRAMEWORK_ROOT: Path = Path(__file__).resolve().parent.parent

TEMPLATES_DIR: Path = FRAMEWORK_ROOT / "templates"
DOCS_DIR: Path = FRAMEWORK_ROOT / "docs"
DASHBOARD_PLUGINS_DIR: Path = FRAMEWORK_ROOT / "dashboard-plugins"

# ── Deployment location ───────────────────────────────────────────────────
# Operator can override via env var; default is ~/.agency.
AGENCY_HOME: Path = Path(os.environ.get("AGENCY_HOME", Path.home() / ".agency")).expanduser()

# Manifest + version pin
DEPLOYMENT_YAML: Path = AGENCY_HOME / "deployment.yaml"
FRAMEWORK_VERSION_LOCK: Path = AGENCY_HOME / "framework-version.lock"

# Shared docs that Sentinel watches over (deployment-local copies)
FRAMEWORK_VAULT: Path = AGENCY_HOME / "framework-vault"
MASTER_PLAN_MD: Path = FRAMEWORK_VAULT / "MASTER_PLAN.md"
DEVELOPMENT_PLAYBOOK_MD: Path = FRAMEWORK_VAULT / "DEVELOPMENT_PLAYBOOK.md"

# Agency-vault — the PRINCIPAL'S context layer (read by agents; owned by operator).
# Goals.md is the single most important document the agency reads — every
# prioritization routes back here. Values.md describes the non-negotiables.
# Personal.md, Work.md, Clients.md provide the situational context CoS uses
# for every triage decision.
AGENCY_VAULT: Path = AGENCY_HOME / "agency-vault"
GOALS_MD: Path = AGENCY_VAULT / "Goals.md"
VALUES_MD: Path = AGENCY_VAULT / "Values.md"
PERSONAL_MD: Path = AGENCY_VAULT / "Personal.md"
WORK_MD: Path = AGENCY_VAULT / "Work.md"
CLIENTS_MD: Path = AGENCY_VAULT / "Clients.md"

# Operator state files — durable memory across sessions. Hermes' injection
# reduces dependency on these, but they remain valuable for cross-session
# continuity (pruned + maintained, they're a clean inbox-to-context channel
# for whatever Hermes-side conversation didn't preserve).
STATE_VAULT: Path = AGENCY_HOME / "state-vault"
OPERATIONAL_STATE_MD: Path = STATE_VAULT / "operational-state.md"
CONVERSATION_JOURNAL_MD: Path = STATE_VAULT / "conversation-journal.md"

# Profiles tree (per-agent content)
PROFILES_DIR: Path = AGENCY_HOME / "profiles"

# Cross-profile state (shared databases)
STATE_DIR: Path = AGENCY_HOME / "_state"
KANBAN_DB: Path = STATE_DIR / "kanban.db"
LEARNING_DB: Path = STATE_DIR / "learning.db"
AUTONOMY_DB: Path = STATE_DIR / "autonomy.db"
EVENTS_DB: Path = STATE_DIR / "events.db"
HEARTBEATS_DB: Path = STATE_DIR / "heartbeats.db"
DRIFT_SCORES_JSON: Path = STATE_DIR / "drift_scores.json"

# Operator-readable health surface
HEALTH_DIR: Path = AGENCY_HOME / "_health"
AUDITS_DIR: Path = HEALTH_DIR / "audits"
OPERATOR_ACTIONS_JSONL: Path = HEALTH_DIR / "operator-actions.jsonl"
RECAPTURE_HISTORY_JSONL: Path = HEALTH_DIR / "recapture-history.jsonl"

# Per-profile derived paths (callers pass profile id, get path)
def profile_dir(profile_id: str) -> Path:
    return PROFILES_DIR / profile_id

def profile_config(profile_id: str) -> Path:
    return profile_dir(profile_id) / "config.yaml"

def profile_auth(profile_id: str) -> Path:
    return profile_dir(profile_id) / "auth.json"

def profile_soul(profile_id: str) -> Path:
    return profile_dir(profile_id) / "SOUL.md"

def profile_standards(profile_id: str) -> Path:
    return profile_dir(profile_id) / "standards.md"

def profile_skills(profile_id: str) -> Path:
    return profile_dir(profile_id) / "skills"

def profile_scripts(profile_id: str) -> Path:
    return profile_dir(profile_id) / "scripts"

def profile_cron_jobs(profile_id: str) -> Path:
    return profile_dir(profile_id) / "cron" / "jobs.json"

def profile_state_db(profile_id: str) -> Path:
    return profile_dir(profile_id) / "state.db"

def profile_logs(profile_id: str) -> Path:
    return profile_dir(profile_id) / "logs"

def profile_vault(profile_id: str) -> Path:
    return profile_dir(profile_id) / "context" / profile_id

# ── Control panel ─────────────────────────────────────────────────────────
CONTROL_PANEL_PORT: int = 9118  # localhost:9118/control-panel

# ── Cron / launchd labels ─────────────────────────────────────────────────
# Per §8.3 of spec: plist labels are framework-fixed except for the
# profile-id portion (the operator's chosen name for the role).
LAUNCHD_LABEL_PREFIX: str = "com.hermes-agency.cron"

def launchd_label(profile_id: str, cron_name: str) -> str:
    return f"{LAUNCHD_LABEL_PREFIX}.{profile_id}.{cron_name}"

# ── Invariants file (single source of truth) ──────────────────────────────
INVARIANTS_YAML: Path = FRAMEWORK_ROOT / "_framework" / "invariants.yaml"


__all__ = [
    "FRAMEWORK_ROOT",
    "TEMPLATES_DIR",
    "DOCS_DIR",
    "DASHBOARD_PLUGINS_DIR",
    "AGENCY_HOME",
    "DEPLOYMENT_YAML",
    "FRAMEWORK_VERSION_LOCK",
    "FRAMEWORK_VAULT",
    "MASTER_PLAN_MD",
    "DEVELOPMENT_PLAYBOOK_MD",
    "AGENCY_VAULT",
    "GOALS_MD",
    "VALUES_MD",
    "PERSONAL_MD",
    "WORK_MD",
    "CLIENTS_MD",
    "STATE_VAULT",
    "OPERATIONAL_STATE_MD",
    "CONVERSATION_JOURNAL_MD",
    "PROFILES_DIR",
    "STATE_DIR",
    "KANBAN_DB",
    "LEARNING_DB",
    "AUTONOMY_DB",
    "EVENTS_DB",
    "HEARTBEATS_DB",
    "DRIFT_SCORES_JSON",
    "HEALTH_DIR",
    "AUDITS_DIR",
    "OPERATOR_ACTIONS_JSONL",
    "RECAPTURE_HISTORY_JSONL",
    "CONTROL_PANEL_PORT",
    "LAUNCHD_LABEL_PREFIX",
    "INVARIANTS_YAML",
    "profile_dir",
    "profile_config",
    "profile_auth",
    "profile_soul",
    "profile_standards",
    "profile_skills",
    "profile_scripts",
    "profile_cron_jobs",
    "profile_state_db",
    "profile_logs",
    "profile_vault",
    "launchd_label",
]
