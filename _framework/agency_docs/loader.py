# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
The actual loader for agency-level aim docs.

Loads (in order, for the canonical "always-loaded background" block):

  1. Goals.md      — the strategic plan (Outcomes + Interim Goals
                     + Initiative refs)
  2. Personal.md   — non-work context (family, health, friendships,
                     hobbies)
  3. Work.md       — what the business actually does
  4. Clients.md    — current roster
  5. SOUL.md       — per-profile voice / character

Each section is delimited and labeled so the model can distinguish
the layers. Missing docs are silently omitted (with a hint in the
returned block when ALL agency-level docs are absent — that's
typically an unconfigured deployment, and the audit picks it up).

Performance note: this is called at every `pre_llm_call`. The
implementation reads the files fresh each time — they're small
(typically <10KB each), and freshness matters more than caching
when the Principal edits them mid-session. If the read cost ever
becomes a bottleneck, mtime-based caching is the obvious add.

Per StrategicPlanning.md §6.2, this is the implementation of "the
always-loaded context — Goals only, not Guardrails."
"""

from __future__ import annotations

from pathlib import Path

from _framework.constants import (
    GOALS_MD,
    PERSONAL_MD,
    WORK_MD,
    CLIENTS_MD,
    AGENCY_HOME,
)


# ── Doc registry ──────────────────────────────────────────────────


# (label, path, optional_explanation_when_absent)
_AIM_DOCS: list[tuple[str, Path]] = [
    ("Goals", GOALS_MD),
    ("Personal context", PERSONAL_MD),
    ("Work context", WORK_MD),
    ("Clients", CLIENTS_MD),
]


def _profile_soul_path(profile: str) -> Path:
    """Path to a profile's SOUL.md within the agency state.

    SOULs live under the profile dir, separate from the
    agency-vault root. We resolve relative to AGENCY_HOME so the
    v0.20 state-collapse path works (~/.hermes/agency-state/profiles/<p>/SOUL.md).
    """
    return AGENCY_HOME / "profiles" / profile / "SOUL.md"


# ── Public API ────────────────────────────────────────────────────


def load_agency_context(profile: str | None = None) -> str:
    """Return the markdown block to prepend to the model's prompt.

    Per spec §1.1, this is the always-loaded background. Called by
    `hermes_agency_plugin.hooks.on_pre_llm_call` every turn.

    Args:
        profile: If given, also loads the per-profile SOUL.md. The
            CoS / BD / Writing / etc. all have a SOUL that gives
            them voice + character; we include the active one
            (not all of them — the active profile is the one
            whose hook fired).

    Returns:
        Markdown block, empty string if nothing is loadable.
    """
    sections: list[str] = []

    for label, path in _AIM_DOCS:
        body = _read_doc(path)
        if body:
            sections.append(f"### {label} (from `{path.name}`)\n\n{body}")

    if profile:
        soul_path = _profile_soul_path(profile)
        soul_body = _read_doc(soul_path)
        if soul_body:
            sections.append(
                f"### Profile SOUL — {profile} (from `{soul_path.name}`)\n\n{soul_body}"
            )

    if not sections:
        return ""

    header = (
        "## Agency-level context (always-loaded background)\n"
        "\n"
        "*The Principal's declared aim. This is what the agency is "
        "operating in service of — present every turn, not the "
        "foreground, but never absent. Guardrails (the brake) are "
        "checked at enforcement-time (Sentinel, send-guard, audit) "
        "and intentionally omitted from this background block.*\n"
        "\n"
    )

    return header + "\n\n".join(sections) + "\n"


def _read_doc(path: Path) -> str:
    """Read a markdown doc, return empty string if absent.

    Caller is the prompt-injection path — silent on missing files
    is correct behavior. The audit's `agency-context-injection`
    rule flags missing docs separately.
    """
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""
    return text


__all__ = ["load_agency_context"]
