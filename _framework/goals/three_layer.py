# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Three-layer Goals.md parser (v0.23.4).

Per StrategicPlanning.md §1 + the v0.22.2-spec Goals.md.template,
strategic Goals.md uses a three-layer structure:

    Goals.md
    ├── Outcome 1 (SMART, 12-60mo)
    │   ├── Interim Goal 1.1 (SMART, 6-12mo)
    │   │   ├── skill: profile/skill-name  (agentic Initiative)
    │   │   └── script: profile/script-name.py  (deterministic Initiative)
    │   └── Interim Goal 1.2 (SMART, 6-12mo)
    │       └── skill: profile/other-skill
    └── Outcome 2 (SMART, 12-60mo)
        └── ...

This module parses that structure. It coexists with the older
flat-list parser in `goals_md.py` (which the legacy Tier 3
wizard still uses); v0.24+ can deprecate that path.

Public API:

    read_goals_strategic(path=None) -> StrategicGoals | None
        None when Goals.md is absent OR when it's in the legacy
        flat format (no Outcomes section). Use `read_goals()` for
        the flat format.

    StrategicGoals — dataclass with:
        outcomes: list[Outcome]
        mission: str (free-text)

    Outcome — dataclass with:
        number: int (1, 2, 3)
        title: str
        statement: str (the SMART statement)
        interim_goals: list[InterimGoal]

    InterimGoal — dataclass with:
        number: str ("1.1", "1.2")
        title: str
        statement: str
        initiative_refs: list[InitiativeRef]

    InitiativeRef — dataclass with:
        kind: "skill" | "script"
        path: str (e.g., "devon/lookalike-prospect-builder")

The audit's unaligned-interim-goals and abandoned-outcome rules
(v0.23.3) consume this parser to cross-check skill frontmatter
declarations against the actual structure in Goals.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from _framework.constants import GOALS_MD


@dataclass
class InitiativeRef:
    kind: str  # "skill" or "script"
    path: str  # e.g., "devon/lookalike-prospect-builder" or "devon/script.py"


@dataclass
class InterimGoal:
    number: str  # "1.1", "1.2"
    title: str = ""
    statement: str = ""
    initiative_refs: list[InitiativeRef] = field(default_factory=list)


@dataclass
class Outcome:
    number: int  # 1, 2, 3
    title: str = ""
    statement: str = ""
    interim_goals: list[InterimGoal] = field(default_factory=list)


@dataclass
class StrategicGoals:
    mission: str = ""
    outcomes: list[Outcome] = field(default_factory=list)

    def all_interim_goal_keys(self) -> list[str]:
        """Return every Interim Goal number (e.g. ['1.1', '1.2', '2.1'])
        — useful for the audit's `unaligned-skills` cross-check."""
        return [
            ig.number
            for o in self.outcomes
            for ig in o.interim_goals
        ]

    def all_outcome_numbers(self) -> list[str]:
        """e.g. ['O1', 'O2', 'O3']."""
        return [f"O{o.number}" for o in self.outcomes]

    def all_initiative_refs(self) -> list[InitiativeRef]:
        """Flatten across all Interim Goals."""
        return [
            ref
            for o in self.outcomes
            for ig in o.interim_goals
            for ref in ig.initiative_refs
        ]


# ── Public API ────────────────────────────────────────────────────


def read_goals_strategic(
    path: Path | str | None = None,
) -> Optional[StrategicGoals]:
    """Parse Goals.md as the three-layer strategic structure.

    Returns None when:
      - the file doesn't exist
      - the file has no `## Outcomes` section (it's in legacy flat
        format; use `read_goals()` from goals_md.py instead)
    """
    p = Path(path) if path else GOALS_MD
    if not p.exists():
        return None

    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if not _looks_like_three_layer(text):
        return None

    return _parse(text)


# ── Internal ──────────────────────────────────────────────────────


_H3_OUTCOME_RE = re.compile(
    r"^###\s+Outcome\s+(\d+)\s*[—–-]\s*(.+?)\s*$",
    re.M,
)
_INTERIM_HEADING_RE = re.compile(
    r"^\*\*Interim\s+Goal\s+([\d.]+)\s*[—–-]\s*(.+?)\*\*\s*$",
    re.M,
)
_INITIATIVE_REF_RE = re.compile(
    r"^-\s+(skill|script):\s+`?([^`*\s]+)`?",
)
_MISSION_HEADING_RE = re.compile(r"^##\s+The\s+mission\s*$", re.M | re.I)
_OUTCOMES_HEADING_RE = re.compile(r"^##\s+Outcomes", re.M)


def _looks_like_three_layer(text: str) -> bool:
    """Heuristic: does the file have an `## Outcomes` section?"""
    return bool(_OUTCOMES_HEADING_RE.search(text))


def _parse(text: str) -> StrategicGoals:
    """Walk the text top-to-bottom, building the structure.

    We don't need a full Markdown AST; the structure is regular
    enough that a line-by-line state machine is reliable and lenient
    (operator-edited text won't always be pristine).
    """
    goals = StrategicGoals()
    goals.mission = _extract_section_body(text, "The mission")

    current_outcome: Optional[Outcome] = None
    current_interim: Optional[InterimGoal] = None
    next_line_is_statement_target: Optional[object] = None  # the dataclass to fill

    for raw in text.splitlines():
        line = raw.rstrip()

        # Outcome heading
        m = _H3_OUTCOME_RE.match(line)
        if m:
            current_outcome = Outcome(
                number=int(m.group(1)),
                title=m.group(2).strip(),
            )
            goals.outcomes.append(current_outcome)
            current_interim = None
            next_line_is_statement_target = current_outcome
            continue

        # Interim Goal heading
        m = _INTERIM_HEADING_RE.match(line)
        if m and current_outcome is not None:
            current_interim = InterimGoal(
                number=m.group(1).strip(),
                title=m.group(2).strip(),
            )
            current_outcome.interim_goals.append(current_interim)
            next_line_is_statement_target = current_interim
            continue

        # Initiative ref
        m = _INITIATIVE_REF_RE.match(line)
        if m and current_interim is not None:
            kind = m.group(1)
            path = m.group(2).strip()
            current_interim.initiative_refs.append(
                InitiativeRef(kind=kind, path=path)
            )
            continue

        # Statement capture — first non-empty, non-heading line after
        # a heading
        if next_line_is_statement_target is not None and line.strip():
            if line.startswith("#") or line.startswith("**"):
                # Hit another heading first; abandon capture
                next_line_is_statement_target = None
            else:
                # Strip leading template placeholders and surrounding
                # markdown emphasis
                cleaned = line.strip()
                if cleaned.startswith("{{") and cleaned.endswith("}}"):
                    # Still a template placeholder — ignore
                    next_line_is_statement_target = None
                else:
                    target = next_line_is_statement_target
                    if hasattr(target, "statement"):
                        target.statement = cleaned
                    next_line_is_statement_target = None
            continue

    return goals


def _extract_section_body(text: str, heading: str) -> str:
    """Return body text after `## {heading}` up to the next `## ` or EOF."""
    pat = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        re.M | re.S | re.I,
    )
    m = pat.search(text)
    if not m:
        return ""
    body = m.group(1).strip()
    # Strip leading template hint blocks if present
    return body


__all__ = [
    "InitiativeRef",
    "InterimGoal",
    "Outcome",
    "StrategicGoals",
    "read_goals_strategic",
]
