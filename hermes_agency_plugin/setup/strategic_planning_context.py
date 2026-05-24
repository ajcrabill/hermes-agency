# PLUGIN — owned by HermesAgency.
"""
Strategic-planning context loader for the setup interview (v0.23.5).

Per spec §13.7 v0.23 Thread B + StrategicPlanning.md §3.5, the
LLM-driven setup interview's prompt must have `StrategicPlanning.md`
§3 and §7.1 loaded as context so the CoS can do silent SMART
translation in the Principal's plain language.

This module returns the context block. Callers (the future
LLM-driven interview, the CoS's `goals-revision-proposal` skill,
the `smart-goal-coach` skill) load it and prepend to their
prompts.

Public API:
    load_strategic_planning_context() -> str
        Returns the §3 + §7.1 markdown content, or a stub block
        if the doc isn't packaged with the deployment.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


# Look for StrategicPlanning.md at known repo locations
_PROBE_PATHS = [
    # Editable install (development): repo's docs/ relative to this file
    Path(__file__).resolve().parent.parent.parent / "docs" / "StrategicPlanning.md",
    # Installed-package location (if we ship the doc inside the wheel)
    Path(__file__).resolve().parent.parent / "docs" / "StrategicPlanning.md",
]


def load_strategic_planning_context() -> str:
    """Return §3 (Quality criteria) + §7.1 (file structure) of
    StrategicPlanning.md as a single context block.

    If the doc can't be located, returns a minimal stub describing
    the SMART canonical form so the interview still has *something*
    to ground on. The audit's `agency-context-injection` rule will
    surface a missing doc separately.
    """
    doc_path = _locate_doc()
    if doc_path is None:
        return _STUB_CONTEXT

    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _STUB_CONTEXT

    section3 = _extract_section(text, "3. Quality criteria")
    section71 = _extract_subsection(text, "7.1 ")
    blocks = [s for s in (section3, section71) if s]
    if not blocks:
        return _STUB_CONTEXT

    return (
        "# Strategic-planning context (loaded by setup interview)\n"
        "\n"
        "*This block carries the framework knowledge the CoS uses to "
        "silently translate the Principal's vision and values into "
        "SMART form. The Principal never sees this content directly; "
        "the CoS keeps it as its own working context.*\n"
        "\n"
        + "\n\n---\n\n".join(blocks)
    )


def _locate_doc() -> Optional[Path]:
    for p in _PROBE_PATHS:
        if p.exists():
            return p
    return None


def _extract_section(text: str, heading_prefix: str) -> str:
    """Pull out the body from `## {heading_prefix}...` to the next `## `.

    `heading_prefix` is matched case-insensitively at the start of
    the H2 text (so "3. Quality criteria" matches "## 3. Quality
    criteria — what good Outcomes...").
    """
    pat = re.compile(
        rf"^##\s+{re.escape(heading_prefix)}.*?$(.*?)(?=^##\s|\Z)",
        re.M | re.S | re.I,
    )
    m = pat.search(text)
    return m.group(0).strip() if m else ""


def _extract_subsection(text: str, heading_prefix: str) -> str:
    """Pull out the body from `### {heading_prefix}...` to the next
    `### ` or `## `."""
    pat = re.compile(
        rf"^###\s+{re.escape(heading_prefix)}.*?$(.*?)(?=^###\s|^##\s|\Z)",
        re.M | re.S | re.I,
    )
    m = pat.search(text)
    return m.group(0).strip() if m else ""


_STUB_CONTEXT = """# Strategic-planning context (minimal stub)

*StrategicPlanning.md not located on this deployment; using a
minimal SMART reference for the interview.*

## SMART canonical form

  <Subject + measure> will increase (or decrease) from <starting
  point> in <starting month/year> to <ending point> by <ending
  month/year>.

- **Specific**: narrow focus of action.
- **Measurable**: starting date + ending date + starting point +
  ending point.
- **Attainable**: ending point reachable by ending date with
  available time, talent, treasure.
- **Results-focused**: tied to vision and/or values.
- **Time-bound**: month/year for start and end (not Q1 / FY).

## The three layers (Outcomes → Interim Goals → Initiatives)

- **Outcomes**: 1-3 SMART statements, 12-60 month horizon. The
  destination.
- **Interim Goals**: 1-3 per Outcome, SMART, 6-12 month horizon.
  Leading indicators.
- **Initiatives**: skills + scripts that produce the outputs.
  Each declares its alignment in SKILL.md frontmatter.

## Guardrails (parallel structure)

- **Guardrails**: prohibition statements (NOT SMART; values made
  enforceable). 1-3 of them.
- **Interim Guardrails**: SMART, measurable. 1-3 per Guardrail.
  The measurable layer; monitoring + audit work happens here.
- If Interim Guardrails are within parameter, the Guardrail is
  inferred honored.
"""


__all__ = ["load_strategic_planning_context"]
