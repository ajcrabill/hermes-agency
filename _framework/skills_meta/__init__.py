# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
SKILL.md frontmatter parser — strategic-planning alignment keys.

Per spec §13.7 v0.23 Thread B + StrategicPlanning.md §5, a
strategic skill or script declares its place in the three-layer
strategic plan via frontmatter keys:

  outcome              — Outcome the skill serves (e.g., "O1")
  interim_goal         — Interim Goal the skill serves (e.g., "G1.1")
  outcome_metric       — SMART statement of what this skill moves
  status               — blue / green / yellow / red / gray
  alignment_argument   — why this skill is predicted to move the
                         Interim Goal (the ≥0.5 correlation claim
                         or leading-indicator argument)
  output_metrics       — mid-cycle indicators of effect
  input_metrics        — effort measures (firing cadence, etc.)
  owner_profile        — the agent profile responsible

These keys are OPTIONAL. A skill without them is "utility work"
— legitimate, but not part of the strategic plan. The audit's
`unaligned-skills` rule (v0.23.3) flags skills that declare an
`interim_goal` but are missing required adjacent fields.

Public API:

  parse_skill_frontmatter(path) -> dict
      Returns a dict of all parsed frontmatter keys (empty if
      none). Strategic-alignment keys are normalized but not
      validated semantically here — validation is the audit's
      job.

  is_strategic_skill(path) -> bool
      True if the skill declares an `interim_goal` (the gating
      key that puts a skill in the strategic plan).

  parse_script_metadata(path) -> dict
      Same shape, but for `.py` / `.sh` scripts. Scripts express
      their alignment metadata in a module-level docstring block
      delimited by `# --- HERMES_AGENCY_META_START` /
      `# --- HERMES_AGENCY_META_END` lines.
"""

from .parser import (
    parse_skill_frontmatter,
    parse_script_metadata,
    is_strategic_skill,
    STRATEGIC_FRONTMATTER_KEYS,
)

__all__ = [
    "parse_skill_frontmatter",
    "parse_script_metadata",
    "is_strategic_skill",
    "STRATEGIC_FRONTMATTER_KEYS",
]
