# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Agent personalization for Tier 3 — per-agent name, pronouns,
personality. Outputs land as appendices to each profile's SOUL.md.

Tier 1's wizard already captures the kebab-case profile id
(`cos`, `kb`, `sentinel`, etc.) — that's the durable identifier
used in paths, kanban assignments, plist labels. Tier 3 layers on
the *human-facing* personality: a display name (which may match the
profile id or differ), pronouns, and a brief personality sketch.

The interview shape per agent:

  1. Display name — same as profile id, or human-named (e.g. "Maya")
  2. Pronouns — she/he/they/it/none
  3. Personality — 2-3 sentences appended to SOUL.md as a header

Skipping any field leaves the default (functional name = profile id;
no pronouns; default SOUL.md content unchanged).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

from _framework.constants import profile_soul


@dataclass
class AgentPersona:
    profile_id: str
    role: str
    display_name: str         # may equal profile_id (functional) or be human-named
    pronouns: str             # "she/her" | "he/him" | "they/them" | "it/its" | ""  (none)
    personality_notes: str    # free-form 2-3 sentences


PRONOUN_OPTIONS = {
    "she": "she/her",
    "he":  "he/him",
    "they": "they/them",
    "it":  "it/its",
    "":    "",          # no pronoun (some operators prefer this)
}


def personalize_agents(
    profiles: Iterable[tuple[str, str]],   # iter of (profile_id, role)
    prompter: Callable[[str, str, str], str] | None = None,
) -> list[AgentPersona]:
    """Walk through each agent and capture personalization.

    `prompter(question, default, hint) -> str`. Tests pass a scripted
    one; interactive default reads stdin.
    """
    prompter = prompter or _interactive_prompter
    out: list[AgentPersona] = []

    print()
    print("─" * 70)
    print("  Per-agent personalization")
    print("─" * 70)
    print(
        "For each agent: an optional human-facing name (vs the\n"
        "functional kebab-case id), preferred pronouns, and a\n"
        "personality sketch the agent's SOUL.md will carry forward.\n"
        "\n"
        "Defaults: functional name, no pronouns, default SOUL.md.\n"
        "Skip any field to leave it at the default.\n"
    )

    for profile_id, role in profiles:
        print()
        print(f"  ── Agent: {profile_id} ({role}) " + "─" * 30)

        display = prompter(
            f"Display name for this agent? (Enter to use functional name '{profile_id}', "
            f"or type a human-facing name like 'Maya')",
            profile_id,
            "",
        )
        display = display.strip() or profile_id

        pronoun_choice = prompter(
            "Pronouns? (she / he / they / it / none)",
            "",
            "Default: none (no pronouns used in SOUL.md prose).",
        ).strip().lower()
        if pronoun_choice in PRONOUN_OPTIONS:
            pronouns = PRONOUN_OPTIONS[pronoun_choice]
        else:
            pronouns = ""

        personality = prompter(
            "Personality sketch (2-3 sentences) — how should this agent come across?",
            "",
            "Examples: 'Calm and methodical, warm without being effusive, direct when asked.'\n"
            "          'Brisk and analytical, ranks evidence over opinion, no diplomatic softening.'\n"
            "Leave blank to use the role's default persona unchanged.",
        ).strip()

        out.append(AgentPersona(
            profile_id=profile_id,
            role=role,
            display_name=display,
            pronouns=pronouns,
            personality_notes=personality,
        ))

    return out


def write_persona_appendices(
    personas: Iterable[AgentPersona],
    interview_date: str,
) -> list[str]:
    """For each persona, append a personalization block to SOUL.md.

    Returns the list of profile_ids actually written. Skipped if the
    operator left everything at default (no display change, no
    pronouns, no personality notes).
    """
    written: list[str] = []
    for p in personas:
        # If nothing meaningful was captured, skip
        if (p.display_name == p.profile_id
                and not p.pronouns
                and not p.personality_notes):
            continue

        soul = profile_soul(p.profile_id)
        if not soul.exists():
            # Profile not yet scaffolded; skip silently
            continue

        block_lines = [
            "",
            "",
            f"## Personalization (from Tier 3 interview {interview_date})",
            "",
        ]
        if p.display_name and p.display_name != p.profile_id:
            block_lines.append(f"- **Display name:** {p.display_name}")
            block_lines.append(
                f"  *(profile id stays `{p.profile_id}` for paths + kanban; "
                f"display name is what humans see)*"
            )
        if p.pronouns:
            block_lines.append(f"- **Pronouns:** {p.pronouns}")
        if p.personality_notes:
            block_lines.append("")
            block_lines.append("**Personality**")
            block_lines.append("")
            block_lines.append(p.personality_notes)

        block = "\n".join(block_lines) + "\n"
        with open(soul, "a", encoding="utf-8") as f:
            f.write(block)
        written.append(p.profile_id)

    return written


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


_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")


def is_safe_id(value: str) -> bool:
    return bool(_SAFE_ID_RE.match(value or ""))


__all__ = [
    "AgentPersona",
    "PRONOUN_OPTIONS",
    "personalize_agents",
    "write_persona_appendices",
    "is_safe_id",
]
