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
    # Hermes engine (set by the Branch A/B step that runs first)
    hermes_home: str = ""
    hermes_binary: str = ""
    hermes_version: str = ""
    hermes_install_source: str = ""      # "existing" | "fresh-clone:<url>@<ref>"
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

    # ── Step 0: Hermes engine (Branch A / B) ───────────────────────────
    # HermesAgency requires Hermes. Detect or install BEFORE anything else.
    if not _hermes_step(answers, prompter):
        return 3   # user aborted or install failed

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
    while True:
        answers.credential_ref = prompter(
            "Credential reference (keychain:NAME or env:VAR; '-' if local-no-auth)",
            f"env:{answers.provider.upper()}_API_KEY",
        ).strip()
        if _looks_like_raw_secret(answers.credential_ref):
            print()
            print("  ✗ That looks like a raw API key, not a reference.")
            print("    deployment.yaml is checked-in / world-readable — never put")
            print("    a raw secret here. Use one of:")
            print()
            print(f"      env:{answers.provider.upper()}_API_KEY   "
                  "(reads from ~/.agency/.env or shell env)")
            print(f"      keychain:hermes-agency-{answers.provider}  "
                  "(reads from macOS Keychain)")
            print("      -                              (local, no auth)")
            print()
            print("    If you have the key in your clipboard, paste it into")
            print(f"    ~/.agency/.env as:  {answers.provider.upper()}_API_KEY=...")
            print("    and then use the env: reference here.")
            print()
            continue
        if answers.credential_ref == "-":
            answers.credential_ref = "env:NONE"  # placeholder; manifest validator will accept it
        break

    print("\n─── Chief of Staff (the agency's voice) " + "─" * 27)
    print("Your CoS is the one face the world sees. She has the only outbound mailbox.")
    print("Tip: profile ids become directory names + path segments. Convention is")
    print("     lowercase (e.g. 'loriah', 'maya'). Capitalized works too but mixing")
    print("     case across profiles in the same deployment is ugly.")
    answers.cos_id = prompter("CoS profile id (your chosen name)", "cos")
    answers.cos_email = prompter("CoS outbound email address", answers.primary_email)

    print("\n─── Knowledge Base + Sentinel (required roles) " + "─" * 20)
    # Adapt the default casing to match what the user chose for CoS — so they
    # don't end up with profiles/Loriah + profiles/sentinel side by side.
    kb_default = _match_case_style(answers.cos_id, "kb")
    sentinel_default = _match_case_style(answers.cos_id, "sentinel")
    answers.kb_id = prompter("Knowledge Base profile id", kb_default)
    answers.sentinel_id = prompter("System Sentinel profile id", sentinel_default)

    # Warn if the user still ended up with inconsistent case
    _warn_if_case_inconsistent([answers.cos_id, answers.kb_id, answers.sentinel_id])

    if tier >= 2:
        # Tier 2 captures defaults here; the substantive interactive
        # flow (OAuth + ingest + cadence + ingress) runs after the
        # manifest + base profiles are provisioned.
        answers.extras["run_tier2"] = True
        answers.extras["ingress.chat_tab"] = True
        for ch in ("signal", "slack"):
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


# ── Hermes engine step (Branch A / B) ─────────────────────────────────────


def _hermes_step(answers: WizardAnswers, prompter: Callable[[str, str], str]) -> bool:
    """The first wizard step — detect an existing Hermes install.

    Plugin discipline (§1.4 of the spec): HermesAgency is a plugin,
    not a runtime, and not an installer of runtimes. If Hermes is
    absent, this step refuses and tells the user to install it via
    NousResearch's official installer first.

    Returns False if Hermes isn't installed or the user aborts —
    caller should propagate exit code 3.
    """
    from _framework.hermes_engine import detect

    print("─── Hermes engine " + "─" * 49)
    print(
        "\n"
        "HermesAgency is a plugin for NousResearch's Hermes engine.\n"
        "We're checking that Hermes is already installed and on PATH.\n"
    )

    info = detect()

    if not info.installed:
        print("  ✗ Hermes is not installed.")
        print()
        print("  HermesAgency is a plugin — it requires Hermes to be installed")
        print("  first. Install Hermes via NousResearch's official installer:")
        print()
        print("      curl -fsSL https://raw.githubusercontent.com/NousResearch/\\")
        print("        hermes-agent/main/scripts/install.sh | bash")
        print()
        print("  Then reload your shell and re-run `agency init`.")
        print()
        print("  Hermes docs: https://hermes-agent.nousresearch.com/docs/")
        return False

    # Detected. Confirm and record.
    print(f"  ✓ Hermes detected (via {info.detected_via}):")
    if info.version:
        print(f"      version: {info.version}")
    print(f"      home:    {info.home}")
    if info.binary:
        print(f"      binary:  {info.binary}")

    confirm = prompter(
        "Use this Hermes install?", "y",
    ).strip().lower()
    if not confirm.startswith("y"):
        custom = prompter(
            "Path to a different HERMES_HOME (leave empty to abort)", "",
        ).strip()
        if not custom:
            print("  Aborted.")
            return False
        custom_path = Path(custom).expanduser().resolve()
        import os as _os
        _os.environ["HERMES_HOME"] = str(custom_path)
        info = detect()
        if not info.installed:
            print(f"  ✗ Couldn't find Hermes at {custom_path}.")
            print("    Expected one of: state.db, kanban.db, scheduler.db, hermes-agent/")
            return False

    answers.hermes_home = str(info.home) if info.home else ""
    answers.hermes_binary = str(info.binary) if info.binary else ""
    answers.hermes_version = info.version or ""
    answers.hermes_install_source = "existing"
    print(f"  ✓ Layering on top of Hermes at {info.home}\n")
    return True


# NOTE: Through v0.13 the wizard had a "Branch B" path that would
# git-clone NousResearch/hermes-agent and pip-install it into a
# user-specified location. That was removed in v0.16 per the plugin
# discipline (§1.4): HermesAgency does not install its own runtime.
# Hermes is installed via NousResearch's `install.sh`, full stop.
# The hermes_engine.installer module is kept for now (used by tests +
# `agency init --hermes-only` recovery) but no wizard path invokes it.


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


def _match_case_style(reference: str, lowercase_default: str) -> str:
    """Adapt a lowercase default to match the case style of a reference.

    If the reference is capitalized (e.g. 'Loriah'), return the default
    capitalized too ('Sentinel'). Otherwise return the lowercase default
    unchanged ('sentinel').
    """
    ref = reference.strip()
    if not ref:
        return lowercase_default
    # First-letter-capitalized? Title-case the default.
    if ref[0].isupper() and ref[1:].islower():
        return lowercase_default[:1].upper() + lowercase_default[1:]
    # Mixed-case (e.g. 'CoS') — leave default as-is; user will override
    # if they want.
    return lowercase_default


def _warn_if_case_inconsistent(ids: list[str]) -> None:
    """Print a warning if profile IDs in this deployment mix case styles.

    Lowercase-and-capitalized side by side (e.g. 'Loriah' + 'sentinel') is
    accepted by the framework but ugly and confusing.
    """
    styles = set()
    for pid in ids:
        if not pid:
            continue
        if pid.islower():
            styles.add("lower")
        elif pid[0].isupper():
            styles.add("capitalized")
        else:
            styles.add("other")
    if len(styles) > 1:
        print()
        print("  ⚠ Profile IDs mix case styles:")
        for pid in ids:
            kind = "Capitalized" if (pid and pid[0].isupper()) else "lowercase"
            print(f"    {pid:20s}  ({kind})")
        print()
        print("    The framework accepts this, but `~/.agency/profiles/Loriah`")
        print("    next to `~/.agency/profiles/sentinel` is confusing. Convention")
        print("    is lowercase. You can fix later with:")
        print("      mv ~/.agency/profiles/<old> ~/.agency/profiles/<new>")
        print("      then edit `id:` in deployment.yaml to match.")
        print()


# Common API-key prefixes that should never appear in a credential REFERENCE.
# (We accept env:NAME, keychain:NAME, env:NONE, '-' — anything else with
# these prefixes is almost certainly a raw secret being pasted by mistake.)
_RAW_SECRET_PREFIXES = (
    "sk-", "pk-",          # OpenAI / Anthropic / DeepSeek / many others
    "xoxb-", "xoxp-",      # Slack
    "ghp_", "gho_",        # GitHub
    "AIza",                # Google API keys (these are 39 chars)
    "AKIA",                # AWS access key id
)


def _looks_like_raw_secret(s: str) -> bool:
    """Heuristic: does this value look like a raw API key vs. a reference?"""
    s = s.strip()
    if not s:
        return False
    # Legitimate references
    if s.startswith(("env:", "keychain:")) or s == "-":
        return False
    # Known secret prefixes
    if any(s.startswith(p) for p in _RAW_SECRET_PREFIXES):
        return True
    # Generic high-entropy: 32+ chars, no spaces, alphanumeric-ish
    if (
        len(s) >= 32
        and " " not in s
        and "/" not in s
        and ":" not in s
        and sum(c.isalnum() for c in s) >= len(s) * 0.8
    ):
        return True
    return False


def _ensure_dirs() -> None:
    from _framework import __version__ as _fw_version
    for d in (AGENCY_HOME, PROFILES_DIR, STATE_DIR, HEALTH_DIR, FRAMEWORK_VAULT, HEALTH_DIR / "audits"):
        d.mkdir(parents=True, exist_ok=True)
    # framework-version.lock
    (AGENCY_HOME / "framework-version.lock").write_text(f"{_fw_version}\n", encoding="utf-8")
    # .env stub for env:VAR credential references
    env_file = AGENCY_HOME / ".env"
    if not env_file.exists():
        env_file.write_text(
            "# HermesAgency environment\n"
            "# Add API keys / secrets here. This file is chmod 600 and\n"
            "# referenced from deployment.yaml as `env:VAR_NAME`.\n"
            "#\n"
            "# Example:\n"
            "#   DEEPSEEK_API_KEY=sk-...\n"
            "#   OPENAI_API_KEY=sk-...\n",
            encoding="utf-8",
        )
        try:
            env_file.chmod(0o600)
        except OSError:
            pass


def _render_manifest(a: WizardAnswers, tier: int) -> str:
    """Produce a manifest body. We don't load the template here — the
    template has placeholders the wizard would have to map anyway.
    Writing the YAML directly is simpler and clearer for v0.1."""
    chat = bool(a.extras.get("ingress.chat_tab", tier >= 2))
    signal = bool(a.extras.get("ingress.signal", False))
    slack = bool(a.extras.get("ingress.slack", False))

    from _framework import __version__ as _fw_version
    return f"""# HermesAgency deployment manifest — generated by `agency init`.
# Edit freely; framework upgrades never overwrite this file.

deployment:
  owner:             {a.owner}
  org_name:          "{a.org_name}"
  primary_email:     {a.primary_email}
  timezone:          {a.timezone}
  framework_version: "{_fw_version}"

engine:
  # The Hermes engine HermesAgency layers on top of. Set by the
  # wizard's Branch A (existing detected) or Branch B (fresh install).
  hermes_home:       "{a.hermes_home}"
  hermes_binary:     "{a.hermes_binary}"
  hermes_version:    "{a.hermes_version}"
  install_source:    "{a.hermes_install_source}"

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
"""


__all__ = ["run_wizard", "WizardAnswers"]
