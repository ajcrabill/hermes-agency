# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Three-tier agency-init wizard.

Tier 1 is the v0.1 ship target: fully working, non-interactive
fallbacks for everything except 4-5 required fields. The operator
can run `agency init` with no args, answer the required prompts,
and end up with a validated deployment in ~5-10 minutes.

Tier 2 and Tier 3 ship in skeleton form in v0.1 (they prompt
explicitly for the v0.2 extension points: OAuth setup, ingest
sources, exemplar capture, multi-identity, content-creation skill
calibration). They print what's coming and write the deployment
with Tier 1 defaults so the operator isn't blocked.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from _framework.constants import (
    AGENCY_HOME,
    DEPLOYMENT_YAML,
    FRAMEWORK_VAULT,
    HEALTH_DIR,
    PROFILES_DIR,
    STATE_DIR,
    TEMPLATES_DIR,
)
from _framework.manifest import validate
from _framework.scaffolds import scaffold_profile


@dataclass
class WizardAnswers:
    owner: str = ""
    org_name: str = ""
    primary_email: str = ""
    timezone: str = ""
    provider: str = ""
    model: str = ""
    base_url: str = ""
    credential_ref: str = ""
    cos_id: str = "cos"
    cos_email: str = ""
    kb_id: str = "kb"
    sentinel_id: str = "sentinel"
    extras: dict = field(default_factory=dict)


def run_wizard(tier: int = 1, prompter: Callable[[str, str], str] | None = None, force: bool = False) -> int:
    """Run the wizard at the requested tier.

    `prompter` is the question-asking function (`prompt, default → answer`).
    Defaults to interactive stdin/stdout. Tests pass a mock prompter.
    """
    prompter = prompter or _interactive_prompt

    if DEPLOYMENT_YAML.exists() and not force:
        print(f"\ndeployment.yaml already exists at {DEPLOYMENT_YAML}.")
        print("Pass --force to overwrite, or edit it directly.\n")
        return 1

    print("=" * 70)
    print(f"  HermesAgency init wizard — Tier {tier}")
    print("=" * 70)
    if tier == 1:
        print(
            "\nTier 1 — Just defaults. We'll ask for what's strictly required\n"
            "(owner, email, model/provider) and accept sensible defaults\n"
            "for everything else. ~5-10 minutes.\n"
        )
    elif tier == 2:
        print(
            "\nTier 2 — Recommended. Tier 1 plus OAuth setup for Gmail/\n"
            "Calendar, ingest source configuration, and ingress channel\n"
            "selection. ~15-30 minutes. (v0.1: this tier currently\n"
            "shows where each extension wires in; full interactive\n"
            "flow ships in v0.2.)\n"
        )
    elif tier == 3:
        print(
            "\nTier 3 — Power user / deep interview. The full setup:\n"
            "exemplar capture per role, IP-corpus bulk import, content-\n"
            "creation skill calibration, multi-identity if needed.\n"
            "~45-60 minutes. (v0.1: this tier currently shows where\n"
            "each piece will plug in; full interactive flow ships in\n"
            "v0.2.)\n"
        )
    else:
        print(f"unknown tier: {tier}", file=sys.stderr)
        return 2

    answers = WizardAnswers()

    print("─── About you and the agency " + "─" * 38)
    answers.owner = prompter("Owner handle (kebab-case, e.g. j-doe)", "")
    answers.org_name = prompter("Organization name (display)", "")
    answers.primary_email = prompter("Your primary email address", "")
    answers.timezone = prompter("Timezone (IANA, e.g. America/Chicago)", "America/Chicago")

    print("\n─── Inference provider " + "─" * 44)
    print("HermesAgency is vendor-neutral. Use any OpenAI-compatible endpoint.")
    answers.provider = prompter(
        "Provider id (e.g. ollama, openai, anthropic, openrouter, deepseek, mistral)",
        "ollama",
    )
    answers.model = prompter("Model id your provider expects", "qwen2.5-coder:7b")
    answers.base_url = prompter("Base URL (OpenAI-compatible)", "http://localhost:11434/v1")
    answers.credential_ref = prompter(
        "Credential reference (keychain:NAME or env:VAR; '-' if local-no-auth)",
        f"env:{answers.provider.upper()}_API_KEY",
    )
    if answers.credential_ref.strip() == "-":
        answers.credential_ref = "env:NONE"  # placeholder; manifest validator will accept it

    print("\n─── Chief of Staff (the agency's voice) " + "─" * 27)
    print("Your CoS is the one face the world sees. She has the only outbound mailbox.")
    answers.cos_id = prompter("CoS profile id (your chosen name)", "cos")
    answers.cos_email = prompter("CoS outbound email address", answers.primary_email)

    print("\n─── Knowledge Base + Sentinel (required roles) " + "─" * 20)
    answers.kb_id = prompter("Knowledge Base profile id", "kb")
    answers.sentinel_id = prompter("System Sentinel profile id", "sentinel")

    if tier >= 2:
        # Tier 2 captures defaults here; the substantive interactive
        # flow (OAuth + ingest + cadence + ingress) runs after the
        # manifest + base profiles are provisioned.
        answers.extras["run_tier2"] = True
        answers.extras["ingress.chat_tab"] = True
        for ch in ("signal", "slack", "openwebui"):
            answers.extras[f"ingress.{ch}"] = False
        print("\n─── Tier 2 setup (queued) " + "─" * 39)
        print("After provisioning, we'll walk through Gmail/Calendar/Drive")
        print("OAuth, ingest sources, digest cadence, and ingress channels.")

    # Tier 3 runs the deep interview AFTER manifest + base profiles are
    # provisioned (the interview needs the cos_id to attach voice notes
    # to its SOUL.md). We mark the flag here and execute after writing.
    if tier >= 3:
        print("\n─── Deep interview (Tier 3) " + "─" * 37)
        print("After we provision the deployment, we'll run the deep")
        print("interview to generate first drafts of:")
        print("  • Goals.md          (agency-level)")
        print("  • Values.md")
        print("  • Personal.md")
        print("  • Work.md")
        print("  • Clients.md")
        print("  • CoS voice refinement (appended to SOUL.md)")
        answers.extras["run_tier3"] = True

    # ── Write deployment skeleton ──────────────────────────────────────
    print("\n─── Writing deployment " + "─" * 44)

    _ensure_dirs()
    body = _render_manifest(answers, tier=tier)
    DEPLOYMENT_YAML.write_text(body, encoding="utf-8")
    print(f"  ✓ wrote {DEPLOYMENT_YAML}")

    # Scaffold the three required profiles
    scaffold_profile(
        role="chief-of-staff",
        profile_id=answers.cos_id,
        substitutions={
            "COS_NAME": _natural_name(answers.cos_id),
            "ORG_NAME": answers.org_name,
            "OWNER_NAME": _natural_name(answers.owner),
            "COS_EMAIL": answers.cos_email,
        },
        force=force,
    )
    print(f"  ✓ scaffolded profile {answers.cos_id} (chief-of-staff)")

    scaffold_profile(
        role="knowledge-base",
        profile_id=answers.kb_id,
        substitutions={
            "KB_NAME": _natural_name(answers.kb_id),
            "ORG_NAME": answers.org_name,
        },
        force=force,
    )
    print(f"  ✓ scaffolded profile {answers.kb_id} (knowledge-base)")

    scaffold_profile(
        role="system-sentinel",
        profile_id=answers.sentinel_id,
        substitutions={
            "SENTINEL_NAME": _natural_name(answers.sentinel_id),
        },
        force=force,
    )
    print(f"  ✓ scaffolded profile {answers.sentinel_id} (system-sentinel)")

    # ── Validate ───────────────────────────────────────────────────────
    print("\n─── Validating deployment.yaml " + "─" * 36)
    result = validate(DEPLOYMENT_YAML)
    if result.ok:
        print("  ✓ manifest valid")
        if result.warnings:
            print(f"  ({len(result.warnings)} warnings — review with `agency status -v`)")
    else:
        print(f"  ⚠ {len(result.errors)} error(s) — review with `agency status -v`")

    # ── Tier 2 interactive flow (runs after base provisioning) ─────────
    if answers.extras.get("run_tier2"):
        from .tier2_flow import run_tier2_flow
        run_tier2_flow(cos_id=answers.cos_id)

    # ── Tier 3 deep interview (runs after base + Tier 2) ───────────────
    if answers.extras.get("run_tier3"):
        from .tier3_interview import run_tier3_interview
        run_tier3_interview(
            owner_name=_natural_name(answers.owner),
            org_name=answers.org_name,
            cos_id=answers.cos_id,
            prompter=None,
            refresh=force,
            profiles_to_personalize=[
                (answers.cos_id, "chief-of-staff"),
                (answers.kb_id, "knowledge-base"),
                (answers.sentinel_id, "system-sentinel"),
            ],
        )

    print("\n" + "=" * 70)
    print("  Next steps")
    print("=" * 70)
    print(f"""
  1. Edit ~/.agency/deployment.yaml to refine any defaults.
  2. Validate again:           agency status -v
  3. Capture a first learning: agency capture "your first correction"
  4. Open the control panel:   https://localhost:9118/control-panel
  5. Read the docs:            docs/ARCHITECTURE.md, docs/ROLES.md

  Your profiles live at {PROFILES_DIR}.
  SOUL.md + standards.md for each are the things to read + edit first.
""")
    return 0


# ── Helpers ──────────────────────────────────────────────────────────────


def _interactive_prompt(question: str, default: str) -> str:
    prompt = f"  {question}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    try:
        ans = input(prompt).strip()
    except EOFError:
        ans = ""
    return ans or default


def _natural_name(s: str) -> str:
    """Convert 'aj-crabill' → 'Aj Crabill', etc. For default substitutions."""
    return " ".join(p.capitalize() for p in s.replace("_", "-").split("-"))


def _ensure_dirs() -> None:
    for d in (AGENCY_HOME, PROFILES_DIR, STATE_DIR, HEALTH_DIR, FRAMEWORK_VAULT, HEALTH_DIR / "audits"):
        d.mkdir(parents=True, exist_ok=True)
    # framework-version.lock
    (AGENCY_HOME / "framework-version.lock").write_text("0.1.0\n", encoding="utf-8")


def _render_manifest(a: WizardAnswers, tier: int) -> str:
    """Produce a manifest body. We don't load the template here — the
    template has placeholders the wizard would have to map anyway.
    Writing the YAML directly is simpler and clearer for v0.1."""
    chat = bool(a.extras.get("ingress.chat_tab", tier >= 2))
    signal = bool(a.extras.get("ingress.signal", False))
    slack = bool(a.extras.get("ingress.slack", False))
    openwebui = bool(a.extras.get("ingress.openwebui", False))

    return f"""# HermesAgency deployment manifest — generated by `agency init`.
# Edit freely; framework upgrades never overwrite this file.

deployment:
  owner:             {a.owner}
  org_name:          "{a.org_name}"
  primary_email:     {a.primary_email}
  timezone:          {a.timezone}
  framework_version: "0.1.0"

profiles:

  - id:            {a.cos_id}
    role:          chief-of-staff
    persona_file:  identities/chief-of-staff.md
    email:         {a.cos_email}
    starter_skills:
      - owner-channels-ingress
      - draft-composer
      - send-orchestrator
      - kanban-orchestrator
      - calendar-manager

  - id:            {a.kb_id}
    role:          knowledge-base
    persona_file:  identities/knowledge-base.md
    email:         null
    starter_skills:
      - ip-curator
      - ip-alignment-check
      - kanban-verdict-publisher

  - id:            {a.sentinel_id}
    role:          system-sentinel
    persona_file:  identities/system-sentinel.md
    email:         null
    starter_skills:
      - learning-monitor
      - heartbeat-watch
      - event-rollup

defaults:
  model:    {a.model}
  provider: {a.provider}
  base_url: {a.base_url}
  fallback_providers: []

credentials:
  {a.provider}: "{a.credential_ref}"

email_access_file: profiles/{a.cos_id}/scripts/learning-system/email-access.md

ingress:
  email:     true
  chat_tab:  {str(chat).lower()}
  signal:    {str(signal).lower()}
  slack:     {str(slack).lower()}
  openwebui: {str(openwebui).lower()}
"""


__all__ = ["run_wizard", "WizardAnswers"]
