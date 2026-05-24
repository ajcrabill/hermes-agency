# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Tier 2 — recommended setup flow.

Tier 1 captured the minimum to boot. Tier 2 layers on the
integration + ingress configuration most agencies want:

  1. Gmail OAuth setup (CoS sends + receives)
  2. Google Calendar OAuth setup
  3. Google Drive OAuth setup
  4. Ingest sources (RSS feeds, newsletter platforms, custom hooks)
  5. Daily digest schedule (when the morning briefing fires)
  6. Ingress channel selection (which channels the operator wants
     to talk to CoS through — email + chat tab default; Signal +
     Slack are opt-in)

~15-30 minutes. Each step is skippable — operator can defer
integrations to later via `agency integrations gmail setup ...`.

The flow is gentle. We don't force OAuth flows the operator
isn't ready to run. Skipping a step records `{ <step>: deferred }`
in the deployment metadata so `agency status` can surface what's
still pending.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from _framework.constants import AGENCY_HOME, DEPLOYMENT_YAML


@dataclass
class Tier2Answers:
    # Integrations
    gmail_setup_now: bool = False
    gmail_client_secret_path: str = ""
    gmail_profile: str = ""
    gmail_scope_preset: str = "modify"

    calendar_setup_now: bool = False
    calendar_client_secret_path: str = ""
    calendar_profile: str = ""

    drive_setup_now: bool = False
    drive_client_secret_path: str = ""
    drive_profile: str = ""

    # Ingest sources
    ingest_sources: list[dict] = field(default_factory=list)

    # Digest cadence
    morning_briefing_time: str = "06:00"
    daily_batch_times: list[str] = field(default_factory=lambda: ["06:00", "13:00", "20:00"])
    weekly_review_dow_time: str = "sun:07:00"

    # Ingress
    ingress_email: bool = True
    ingress_chat_tab: bool = True
    ingress_signal: bool = False
    ingress_slack: bool = False

    deferred_steps: list[str] = field(default_factory=list)


def run_tier2_flow(
    *,
    cos_id: str,
    prompter: Callable[[str, str, str], str] | None = None,
    setup_integration: Callable[[str, str, str], None] | None = None,
) -> Tier2Answers:
    """Walk the operator through Tier 2 configuration.

    `prompter(question, default, hint) -> answer` — tests pass a
    scripted version. `setup_integration(name, profile, client_secret_path)
    -> None` runs the actual OAuth flow for a specific integration; tests
    pass a no-op stub.
    """
    prompter = prompter or _interactive_prompter
    setup_integration = setup_integration or _default_integration_setup

    a = Tier2Answers()
    a.gmail_profile = cos_id
    a.calendar_profile = cos_id
    a.drive_profile = cos_id

    print()
    print("=" * 70)
    print("  Tier 2 — Recommended setup")
    print("=" * 70)
    print("""
About 15-30 minutes. We'll walk through Gmail / Calendar / Drive
OAuth setup, ingest sources, digest cadence, and ingress channels.

Each step is skippable. Skipped steps land as `deferred` in the
deployment metadata — `agency status` surfaces what's still pending.
You can run any setup later with `agency integrations <name> setup`.
""")

    # ── Step 1-3: Google OAuth integrations ─────────────────────────────
    a.gmail_setup_now = _yn(prompter,
        "Set up Gmail OAuth now? (CoS sends/receives email)",
        default="n",
    )
    if a.gmail_setup_now:
        a.gmail_client_secret_path = prompter(
            "Path to Gmail client_secret.json (from your GCP project)",
            "", "Download from console.cloud.google.com → APIs → Credentials.",
        )
        a.gmail_scope_preset = prompter(
            "Gmail scope preset (readonly / send / modify)",
            "modify",
            "modify is the most common — covers reading inbox + sending + label changes.",
        ) or "modify"
        try:
            setup_integration("gmail", a.gmail_profile,
                              client_secret=a.gmail_client_secret_path)
            print(f"  ✓ Gmail wired to profile {a.gmail_profile}")
        except Exception as e:
            print(f"  ⚠ Gmail setup deferred: {e}")
            a.deferred_steps.append("gmail")
    else:
        a.deferred_steps.append("gmail")

    a.calendar_setup_now = _yn(prompter,
        "Set up Google Calendar OAuth now? (calendar-manager skill)",
        default="n",
    )
    if a.calendar_setup_now:
        a.calendar_client_secret_path = prompter(
            "Path to Calendar client_secret.json",
            "", "Often the same client_secret.json as Gmail works.",
        )
        try:
            setup_integration("google-calendar", a.calendar_profile,
                              client_secret=a.calendar_client_secret_path)
            print(f"  ✓ Calendar wired to profile {a.calendar_profile}")
        except Exception as e:
            print(f"  ⚠ Calendar setup deferred: {e}")
            a.deferred_steps.append("calendar")
    else:
        a.deferred_steps.append("calendar")

    a.drive_setup_now = _yn(prompter,
        "Set up Google Drive OAuth now? (CoS file upload + share)",
        default="n",
    )
    if a.drive_setup_now:
        a.drive_client_secret_path = prompter(
            "Path to Drive client_secret.json", "",
            "Same client_secret.json as Gmail/Calendar usually works.",
        )
        try:
            setup_integration("google-drive", a.drive_profile,
                              client_secret=a.drive_client_secret_path)
            print(f"  ✓ Drive wired to profile {a.drive_profile}")
        except Exception as e:
            print(f"  ⚠ Drive setup deferred: {e}")
            a.deferred_steps.append("drive")
    else:
        a.deferred_steps.append("drive")

    # ── Step 4: Ingest sources ──────────────────────────────────────────
    print()
    print("─" * 70)
    print("  Ingest sources")
    print("─" * 70)
    print("""
Optional. RSS feeds, newsletter platforms, custom hooks that the
agency should poll. CoS routes inbound items from these channels
through the same triage as email.
""")
    while True:
        kind = prompter(
            "Add an ingest source? (rss / atom / webhook / none-stop)",
            "none-stop",
            "Press Enter to stop adding sources.",
        ).strip().lower()
        if not kind or kind == "none-stop":
            break
        url = prompter("Source URL", "", "")
        if not url:
            break
        name = prompter("Display name for this source", url[:40], "")
        a.ingest_sources.append({"kind": kind, "url": url, "name": name})
        print(f"  + Added ingest source: {name}")
    if not a.ingest_sources:
        a.deferred_steps.append("ingest_sources")

    # ── Step 5: Digest cadence ──────────────────────────────────────────
    print()
    print("─" * 70)
    print("  Daily + weekly digest cadence")
    print("─" * 70)
    a.morning_briefing_time = prompter(
        "Morning briefing time (HH:MM 24h, deployment timezone)",
        "06:00", "",
    )
    batch_raw = prompter(
        "Triage batch times (comma-separated HH:MM list)",
        "06:00,13:00,20:00",
        "Three is typical; pick the moments you actually read the queue.",
    )
    a.daily_batch_times = [t.strip() for t in batch_raw.split(",") if t.strip()]
    a.weekly_review_dow_time = prompter(
        "Weekly review (DOW:HH:MM, e.g. sun:07:00)",
        "sun:07:00", "Sunday morning is the spec default.",
    )

    # ── Step 6: Ingress channels ────────────────────────────────────────
    print()
    print("─" * 70)
    print("  Ingress channels — how you talk to CoS")
    print("─" * 70)
    print("""
Email and the dashboard chat tab default to ON.
The others are opt-in — they require additional setup beyond Tier 2.
""")
    a.ingress_email = True   # always on
    a.ingress_chat_tab = _yn(prompter,
        "Enable dashboard chat-tab ingress?", default="y")
    a.ingress_signal = _yn(prompter,
        "Enable Signal ingress? (requires signal-cli setup later)",
        default="n")
    a.ingress_slack = _yn(prompter,
        "Enable Slack ingress? (requires slack app setup later)",
        default="n")

    # ── Persist into deployment.yaml ────────────────────────────────────
    _persist_to_deployment_yaml(a)

    print()
    print("=" * 70)
    print("  Tier 2 complete")
    print("=" * 70)
    if a.deferred_steps:
        print(f"  Deferred (run later): {', '.join(a.deferred_steps)}")
    print(f"  Deployment manifest updated: {DEPLOYMENT_YAML}")
    print()
    return a


# ── Helpers ─────────────────────────────────────────────────────────────


def _interactive_prompter(question: str, default: str, hint: str) -> str:
    print()
    print(f"  Q: {question}")
    if hint:
        for line in hint.splitlines():
            print(f"     {line}")
    if default:
        print(f"     [Enter to accept: {default}]")
    try:
        ans = input("     > ").strip()
    except EOFError:
        ans = ""
    return ans or default


def _yn(prompter: Callable[[str, str, str], str], question: str,
        *, default: str = "n") -> bool:
    ans = prompter(question, default, "y / n").strip().lower()
    return ans.startswith("y")


def _default_integration_setup(name: str, profile: str, client_secret: str) -> None:
    """Default: invoke each integration's setup_interactive."""
    if not client_secret:
        raise ValueError("no client_secret path provided")
    if name == "gmail":
        from _framework.integrations.gmail import setup_interactive
        setup_interactive(profile, client_secret)
    elif name == "google-calendar":
        from _framework.integrations.google_calendar import setup_interactive
        setup_interactive(profile, client_secret)
    elif name == "google-drive":
        from _framework.integrations.google_drive import setup_interactive
        setup_interactive(profile, client_secret)
    else:
        raise ValueError(f"unknown integration: {name}")


def _persist_to_deployment_yaml(a: Tier2Answers) -> None:
    """Update deployment.yaml::ingress + tier2 sections."""
    if not DEPLOYMENT_YAML.exists():
        return
    text = DEPLOYMENT_YAML.read_text(encoding="utf-8")
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return

    # ingress
    doc.setdefault("ingress", {})
    doc["ingress"].update({
        "email": a.ingress_email,
        "chat_tab": a.ingress_chat_tab,
        "signal": a.ingress_signal,
        "slack": a.ingress_slack,
    })

    # tier2 metadata (digests, ingest sources, deferred steps)
    doc.setdefault("tier2", {})
    doc["tier2"].update({
        "morning_briefing_time": a.morning_briefing_time,
        "daily_batch_times": a.daily_batch_times,
        "weekly_review_dow_time": a.weekly_review_dow_time,
        "ingest_sources": a.ingest_sources,
        "deferred_steps": a.deferred_steps,
    })

    DEPLOYMENT_YAML.write_text(
        yaml.safe_dump(doc, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


__all__ = ["Tier2Answers", "run_tier2_flow"]
