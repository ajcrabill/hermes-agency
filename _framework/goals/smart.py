# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
SMART criteria checker.

  S — Specific:   clear what / who / where
  M — Measurable: a number or binary success criterion
  A — Achievable: caller-asserted (depends on resources; we don't
                  know enough to judge, so we leave this to the
                  operator and the coaching dialogue)
  R — Relevant:   ties to a higher goal / mission
  T — Time-bound: has a deadline

This is a heuristic checker — it scores each dimension 0/1 with a
brief reason. The LLM-driven coach uses these signals to drive
follow-up questions ("missing T — by when?").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SmartVerdict:
    """Per-dimension scoring + overall verdict."""

    specific: bool
    specific_reason: str
    measurable: bool
    measurable_reason: str
    relevant: bool
    relevant_reason: str
    time_bound: bool
    time_bound_reason: str
    # Achievable is operator-asserted; we surface a placeholder
    achievable_note: str = "Achievability depends on resources — assess against current capacity."
    missing: list[str] = field(default_factory=list)

    @property
    def is_smart(self) -> bool:
        """True if specific + measurable + relevant + time_bound all pass.
        Achievable is operator-judged separately."""
        return self.specific and self.measurable and self.relevant and self.time_bound

    def render(self) -> str:
        ok = "✓"
        no = "✗"
        lines = [
            f"  {ok if self.specific else no} **Specific** — {self.specific_reason}",
            f"  {ok if self.measurable else no} **Measurable** — {self.measurable_reason}",
            f"  ·  **Achievable** — {self.achievable_note}",
            f"  {ok if self.relevant else no} **Relevant** — {self.relevant_reason}",
            f"  {ok if self.time_bound else no} **Time-bound** — {self.time_bound_reason}",
        ]
        if self.missing:
            lines.append("")
            lines.append("**Follow-up questions:**")
            for m in self.missing:
                lines.append(f"  - {m}")
        return "\n".join(lines)


# ── Pattern detectors ───────────────────────────────────────────────────


_VAGUE_VERBS = {
    "grow", "improve", "increase", "enhance", "develop", "build",
    "expand", "strengthen", "support", "help", "ensure", "leverage",
    "maximize", "optimize", "deliver",
}
_SPECIFIC_NOUNS_RE = re.compile(
    r"\b(client|customer|user|district|book|chapter|episode|article|"
    r"newsletter|workshop|talk|book|cohort|deal|account|partner|"
    r"meeting|call|launch|release|version|release)\b",
    re.IGNORECASE,
)

_NUMBER_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:%|percent|x)?\b")
_MEASURE_WORDS_RE = re.compile(
    r"\b(by|to|at least|at most|no more than|at|reach|achieve|grow to|"
    r"complete|deliver|publish|ship|sign|close|earn|hit|score)\b",
    re.IGNORECASE,
)

_TIME_WORDS_RE = re.compile(
    r"\b(by (?:end of )?(?:q[1-4]|quarter|month|year|january|february|march|april|may|june|july|august|september|october|november|december|\d{4}|\d+(?:st|nd|rd|th)?)|"
    r"this (?:week|month|quarter|year)|"
    r"within \d+\s+(?:days?|weeks?|months?|quarters?|years?)|"
    r"before \w+|"
    r"by \d{4}|by \d{1,2}/\d{1,2}|by \d{1,2}-\d{1,2})\b",
    re.IGNORECASE,
)

_RELEVANT_LINK_RE = re.compile(
    r"\b(in service of|to enable|so that|because|as part of|toward|"
    r"supporting|advancing|contributing to|aligned with|serves|"
    r"connects to|ladders to|rolls up to)\b",
    re.IGNORECASE,
)


def smart_check(goal_text: str) -> SmartVerdict:
    """Score a goal statement against SMART criteria.

    Returns a SmartVerdict with per-dimension pass/fail + reasons +
    follow-up questions for any failing dimensions.
    """
    text = (goal_text or "").strip()
    missing: list[str] = []

    # ── S — Specific ────────────────────────────────────────────────
    specific = False
    specific_reason = ""
    if not text:
        specific_reason = "empty goal — what specifically?"
        missing.append("What specifically does success look like?")
    else:
        words = text.lower().split()
        starts_vague = any(w in _VAGUE_VERBS for w in words[:5])
        has_specific_noun = bool(_SPECIFIC_NOUNS_RE.search(text))
        if has_specific_noun and not starts_vague:
            specific = True
            specific_reason = "clear subject + concrete verb"
        elif has_specific_noun:
            specific = True
            specific_reason = "concrete subject named (though opening verb is broad)"
        else:
            specific_reason = "no concrete subject (clients / districts / books / etc.)"
            missing.append("What's the concrete subject? (clients / chapters / "
                           "districts / talks / deals — pick the right noun)")

    # ── M — Measurable ──────────────────────────────────────────────
    has_number = bool(_NUMBER_RE.search(text))
    has_measure_word = bool(_MEASURE_WORDS_RE.search(text))
    if has_number and has_measure_word:
        measurable = True
        measurable_reason = "explicit number + measurable verb"
    elif has_number:
        measurable = True
        measurable_reason = "number present (verb implies measurement)"
    elif _is_binary_outcome(text):
        measurable = True
        measurable_reason = "binary outcome — done / not done"
    else:
        measurable = False
        measurable_reason = "no number + not a binary outcome"
        missing.append("What number tells you it happened? Or is this a binary "
                       "did-it-ship outcome?")

    # ── R — Relevant ────────────────────────────────────────────────
    has_link = bool(_RELEVANT_LINK_RE.search(text))
    if has_link:
        relevant = True
        relevant_reason = "explicit link to a higher goal"
    elif len(text.split()) > 25:
        # Long goals usually include their justification implicitly
        relevant = True
        relevant_reason = "long-form goal — relevance likely captured in context"
    else:
        relevant = False
        relevant_reason = "no explicit link to mission / higher goal"
        missing.append("How does this serve the agency's mission? Connect it to "
                       "the higher goal it ladders to.")

    # ── T — Time-bound ──────────────────────────────────────────────
    has_time = bool(_TIME_WORDS_RE.search(text))
    if has_time:
        time_bound = True
        time_bound_reason = "deadline present"
    else:
        time_bound = False
        time_bound_reason = "no explicit deadline"
        missing.append("By when? (specific date, end-of-quarter, end-of-year, etc.)")

    return SmartVerdict(
        specific=specific, specific_reason=specific_reason,
        measurable=measurable, measurable_reason=measurable_reason,
        relevant=relevant, relevant_reason=relevant_reason,
        time_bound=time_bound, time_bound_reason=time_bound_reason,
        missing=missing,
    )


def _is_binary_outcome(text: str) -> bool:
    """Heuristic: looks like a "ship X" / "launch Y" / "publish Z" goal
    that's either done or not."""
    binary_verbs = ("ship", "launch", "publish", "release", "complete",
                    "finish", "open", "close", "deliver")
    first_words = text.lower().split()[:3]
    return any(v in first_words for v in binary_verbs)


__all__ = ["SmartVerdict", "smart_check"]
