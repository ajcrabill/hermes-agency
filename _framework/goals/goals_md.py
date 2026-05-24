# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Goals.md round-trip — parse + structured edit + write-back.

The doc lives at `{{AGENCY_VAULT}}/Goals.md` (from constants.GOALS_MD).
It's a human-edited markdown file; agents add or refine entries
under specific H2 sections without disturbing the rest.

Section structure (per Tier 3 template):
  # Goals — <ORG>
  ## The mission
  ## The current year's goals    (we call this ANNUAL_GOALS)
  ## Active strategic projects
  ## What we're NOT working on
  ## How we measure progress
  ## Decision principles when goals conflict
  ## Goal review cadence

The parser captures each H2 section's content. Editors add/replace
specific bullets in `ANNUAL_GOALS` and `Active strategic projects`
without touching surrounding sections.

Interim milestones are sub-bullets under each annual goal — the
parser preserves them as a nested list per goal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from _framework.constants import GOALS_MD


# H2 headers we know about. Order matters for write-back.
SECTION_HEADERS: list[str] = [
    "The mission",
    "The current year's goals",
    "Active strategic projects",
    "What we're NOT working on",
    "How we measure progress",
    "Decision principles when goals conflict",
    "Goal review cadence",
]


@dataclass
class AnnualGoal:
    """One annual goal + its interim milestones (sub-bullets)."""

    text: str                          # the top-level bullet text
    interim: list[str] = field(default_factory=list)   # sub-bullets


@dataclass
class ParsedGoals:
    """Structured view of Goals.md."""

    title_line: str = ""               # the H1 (e.g. "# Goals — Org Name")
    sections: dict[str, str] = field(default_factory=dict)
    # Special: ANNUAL_GOALS gets structured parsing for edit operations
    annual_goals: list[AnnualGoal] = field(default_factory=list)
    raw_text: str = ""                 # original file content

    def section(self, header: str) -> str:
        return self.sections.get(header, "")


# ── Parsing ─────────────────────────────────────────────────────────────


_H1_RE = re.compile(r"^#\s+(.+)$", re.M)
_H2_RE = re.compile(r"^##\s+(.+)$", re.M)
_TOP_BULLET_RE = re.compile(r"^\s{0,1}[-*]\s+(.+)$")
_SUB_BULLET_RE = re.compile(r"^\s{2,4}[-*]\s+(.+)$")


def read_goals(path: Path | str | None = None) -> ParsedGoals:
    """Parse the Goals.md file at GOALS_MD (or override)."""
    p = Path(path or GOALS_MD).expanduser()
    if not p.exists():
        return ParsedGoals(sections={h: "" for h in SECTION_HEADERS})

    text = p.read_text(encoding="utf-8")
    parsed = ParsedGoals(raw_text=text)

    # Title (H1)
    h1 = _H1_RE.search(text)
    if h1:
        parsed.title_line = h1.group(0)

    # Split into H2-delimited sections
    sections: dict[str, str] = {}
    h2_positions = [(m.start(), m.group(1).strip(), m.end()) for m in _H2_RE.finditer(text)]
    for i, (start, header, end_of_h2) in enumerate(h2_positions):
        end = h2_positions[i + 1][0] if i + 1 < len(h2_positions) else len(text)
        body = text[end_of_h2:end].strip("\n")
        sections[header] = body
    parsed.sections = sections

    # Special structured parsing of the annual-goals section
    parsed.annual_goals = _parse_annual_goals(
        sections.get("The current year's goals", "")
    )
    return parsed


def _parse_annual_goals(section_text: str) -> list[AnnualGoal]:
    """Parse the annual-goals section into structured goals + interim."""
    out: list[AnnualGoal] = []
    current: AnnualGoal | None = None
    for line in section_text.splitlines():
        sub = _SUB_BULLET_RE.match(line)
        if sub and current is not None:
            current.interim.append(sub.group(1).strip())
            continue
        top = _TOP_BULLET_RE.match(line)
        if top:
            if current is not None:
                out.append(current)
            current = AnnualGoal(text=top.group(1).strip())
            continue
        # blank line or other content — terminate any in-flight goal
        # only if we're between bullets (preserve placeholders etc.)
    if current is not None:
        out.append(current)
    return out


# ── Editing ─────────────────────────────────────────────────────────────


def add_annual_goal(
    text: str,
    *,
    interim: list[str] | None = None,
    path: Path | str | None = None,
) -> ParsedGoals:
    """Append a new annual goal (with optional interim milestones)."""
    parsed = read_goals(path)
    parsed.annual_goals.append(
        AnnualGoal(text=text.strip(), interim=[i.strip() for i in (interim or [])])
    )
    _write_back(parsed, path)
    return parsed


def replace_annual_goal(
    index: int,
    text: str,
    *,
    interim: list[str] | None = None,
    path: Path | str | None = None,
) -> ParsedGoals:
    """Replace the goal at the given 0-based index."""
    parsed = read_goals(path)
    if not (0 <= index < len(parsed.annual_goals)):
        raise IndexError(
            f"annual_goals index {index} out of range "
            f"(have {len(parsed.annual_goals)})"
        )
    parsed.annual_goals[index] = AnnualGoal(
        text=text.strip(),
        interim=[i.strip() for i in (interim or [])],
    )
    _write_back(parsed, path)
    return parsed


def add_active_project(
    text: str,
    *,
    details: list[str] | None = None,
    path: Path | str | None = None,
) -> ParsedGoals:
    """Append a new active project (top-level bullet + optional detail lines)."""
    parsed = read_goals(path)
    section = parsed.sections.get("Active strategic projects", "")
    new_block = f"- **{text.strip()}**"
    if details:
        for d in details:
            new_block += f"\n  - {d.strip()}"
    # Append cleanly (preserve any preamble paragraph above the bullets)
    if section.rstrip():
        parsed.sections["Active strategic projects"] = (
            section.rstrip() + "\n" + new_block + "\n"
        )
    else:
        parsed.sections["Active strategic projects"] = new_block + "\n"
    _write_back(parsed, path)
    return parsed


# ── Write-back ──────────────────────────────────────────────────────────


def _write_back(parsed: ParsedGoals, path: Path | str | None = None) -> None:
    """Render the parsed structure back to disk, preserving any
    sections we didn't touch + the section ordering."""
    target = Path(path or GOALS_MD).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # Preserve preamble before the first H2 (title + any explanatory text)
    text = parsed.raw_text
    if text:
        first_h2 = _H2_RE.search(text)
        if first_h2:
            lines.append(text[:first_h2.start()].rstrip())
        else:
            lines.append(text.rstrip())
    elif parsed.title_line:
        lines.append(parsed.title_line)
    else:
        lines.append("# Goals\n\n_The single most important document the agency reads._\n")

    # Walk known section headers in order; emit ANNUAL_GOALS specially
    for header in SECTION_HEADERS:
        lines.append("")
        lines.append(f"## {header}")
        if header == "The current year's goals":
            lines.append("")
            body = _render_annual_goals(parsed.annual_goals)
            lines.append(body)
        else:
            body = parsed.sections.get(header, "")
            if body.strip():
                lines.append("")
                lines.append(body.strip())

    # Any sections that exist in parsed.sections but aren't in our known
    # list — emit at the end (operators may have added their own H2)
    known = set(SECTION_HEADERS)
    for header, body in parsed.sections.items():
        if header in known:
            continue
        lines.append("")
        lines.append(f"## {header}")
        if body.strip():
            lines.append("")
            lines.append(body.strip())

    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _render_annual_goals(goals: list[AnnualGoal]) -> str:
    if not goals:
        return "_(none yet — add via `agency goals add`)_\n"
    out_lines: list[str] = []
    for g in goals:
        out_lines.append(f"- {g.text}")
        for m in g.interim:
            out_lines.append(f"  - {m}")
    return "\n".join(out_lines)


__all__ = [
    "AnnualGoal", "ParsedGoals",
    "SECTION_HEADERS",
    "read_goals",
    "add_annual_goal", "replace_annual_goal",
    "add_active_project",
]
