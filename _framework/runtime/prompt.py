# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Prompt composer.

Builds the system prompt for a chat session by stacking:

  1. The profile's SOUL.md           (who I am)
  2. The profile's standards.md      (the floor I won't fall below)
  3. Applicable learning rules       (from learning.db, via rule_injection)
  4. A short framing footer          (you're CoS, respond in your voice, etc.)

This is the *minimum* that lets an out-of-the-box CoS feel like the
specific principal's CoS — and the gate that makes the 270 v7 rules
actually start applying to live responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from _framework.constants import profile_dir, profile_soul, profile_standards
from _framework.learning.rule_injection import inject_for_skill


@dataclass
class ComposedPrompt:
    system: str
    rules_count: int          # how many learning rules made it into the prompt
    profile_used: str
    voice_tags: list[str]


def compose_chat_prompt(
    profile: str,
    role: str = "chief-of-staff",
    voice_tags: list[str] | None = None,
    skill_tag: str = "interactive-chat",
) -> ComposedPrompt:
    """Assemble the full system prompt for an interactive chat session.

    `skill_tag` is used as the synthetic skill name for rule resolution
    (so chat sessions can pick up rules tagged 'general' or role-level
    rules). Defaults to 'interactive-chat' but the operator can override
    to mimic a specific skill's rule set.
    """
    voice_tags = voice_tags or []

    sections: list[str] = []

    # 1. SOUL.md
    soul = profile_soul(profile)
    if soul.exists():
        sections.append(f"# Identity ({profile}'s SOUL)\n\n{soul.read_text(encoding='utf-8').strip()}")
    else:
        sections.append(
            f"# Identity\n\nYou are {profile}, the Chief of Staff for this agency. "
            f"(No SOUL.md was found at {soul}; deploy one for a richer persona.)"
        )

    # 2. standards.md
    stds = profile_standards(profile)
    if stds.exists():
        sections.append(f"# Standards ({profile}'s quality floor)\n\n{stds.read_text(encoding='utf-8').strip()}")

    # 3. Applicable learning rules
    rules_block = inject_for_skill(
        skill_name=skill_tag,
        profile=profile,
        role=role,
        voice_tags=voice_tags,
    )
    rules_count = 0
    if rules_block:
        sections.append(rules_block)
        # Count the bullet lines as a proxy for rule count
        rules_count = sum(1 for line in rules_block.splitlines() if line.startswith("- "))

    # 4. Framing footer
    sections.append(
        "# This session\n\n"
        "This is an interactive chat with your principal. Respond in your "
        "voice (per SOUL above) and within your standards (per Standards "
        "above). Apply the supervised-learning rules listed above without "
        "being prompted to.\n\n"
        "When you act on a rule above, mention which rule id you used "
        "(e.g. \"per lr042\") — this records the rule's firing so the "
        "learning loop's recapture detector knows it stayed live."
    )

    return ComposedPrompt(
        system="\n\n---\n\n".join(sections),
        rules_count=rules_count,
        profile_used=profile,
        voice_tags=voice_tags,
    )


__all__ = ["ComposedPrompt", "compose_chat_prompt"]
