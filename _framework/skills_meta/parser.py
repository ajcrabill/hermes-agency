# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
SKILL.md frontmatter parser implementation.

See `__init__.py` for the public-API contract and the design
rationale (StrategicPlanning.md §5).

Frontmatter format (the v0.23+ strategic-alignment keys are a
superset of the pre-v0.23 keys like `skill_id`, `profile`, etc.):

```
---
skill_id: weekly-review
profile: loriah
role: chief-of-staff
# Strategic-alignment keys (optional; skills with these are
# part of the three-layer plan):
outcome: O1
interim_goal: G1.1
outcome_metric: "Engagements will increase from 5 in Jan 2026 to 9 by Dec 2026"
status: green
alignment_argument: "Each weekly review surfaces blockers within 7d"
output_metrics:
  - blockers_surfaced_per_week
  - principal_decisions_per_week
input_metrics:
  - firings_per_week: 1
owner_profile: cos
---
```

For scripts:

```python
\"\"\"
This is the module docstring.
\"\"\"

# --- HERMES_AGENCY_META_START
# outcome: O1
# interim_goal: G1.1
# outcome_metric: "..."
# status: green
# --- HERMES_AGENCY_META_END

# real code follows
```

The parser is intentionally lenient. YAML is a superset of what
operators actually edit; we accept simple `key: value` lines
without requiring full YAML correctness. Lists are recognized
either as `[a, b, c]` inline or as `- item` continuation lines.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


STRATEGIC_FRONTMATTER_KEYS = (
    "outcome",
    "interim_goal",
    "outcome_metric",
    "status",
    "alignment_argument",
    "output_metrics",
    "input_metrics",
    "owner_profile",
)


def parse_skill_frontmatter(path: Path | str) -> dict[str, Any]:
    """Parse the YAML frontmatter block at the top of a SKILL.md.

    Returns:
        Dict of all parsed keys. Strategic-alignment keys are
        included if present. Empty dict if no frontmatter block
        or if the file can't be read.
    """
    text = _safe_read(path)
    if not text:
        return {}

    block = _extract_frontmatter_block(text)
    if not block:
        return {}

    return _parse_yaml_lite(block)


def parse_script_metadata(path: Path | str) -> dict[str, Any]:
    """Parse the HERMES_AGENCY_META block out of a script's source.

    Looks for the `# --- HERMES_AGENCY_META_START` / `# ---
    HERMES_AGENCY_META_END` delimiters in the script and parses
    the lines between them as key:value pairs (stripping the
    leading `# `).

    Returns:
        Dict of parsed keys, empty dict if no META block.
    """
    text = _safe_read(path)
    if not text:
        return {}

    m = re.search(
        r"#\s*---\s*HERMES_AGENCY_META_START(.*?)#\s*---\s*HERMES_AGENCY_META_END",
        text,
        re.DOTALL,
    )
    if not m:
        return {}

    # Strip leading "# " from each line within the block
    block_lines: list[str] = []
    for raw in m.group(1).splitlines():
        s = raw.strip()
        if s.startswith("#"):
            s = s[1:].lstrip()
        if s:
            block_lines.append(s)
    return _parse_yaml_lite("\n".join(block_lines))


def is_strategic_skill(path: Path | str) -> bool:
    """True if the skill declares an `interim_goal` in its frontmatter.

    `interim_goal` is the gating key that puts a skill in the
    strategic plan. Skills without it are utility work.
    """
    frontmatter = parse_skill_frontmatter(path)
    return bool(frontmatter.get("interim_goal"))


# ── Internal helpers ─────────────────────────────────────────────


def _safe_read(path: Path | str) -> str:
    """Read text, returning empty string on any IO error."""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _extract_frontmatter_block(text: str) -> str:
    """Pull out the body between the leading `---` lines.

    Returns empty string if the file doesn't open with `---`
    (frontmatter is absent).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    out: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(out)
        out.append(line)
    return ""  # unterminated frontmatter; treat as absent


def _parse_yaml_lite(block: str) -> dict[str, Any]:
    """A lenient parser for the subset of YAML our SKILL.md files use.

    Handles:
      - `key: value` (string)
      - `key: [a, b, c]` (inline list)
      - `key:` followed by indented `- item` lines (block list)
      - Nested dicts (one level deep, for `autonomy:` etc.)

    Strings with special characters can be quoted (single or
    double). Quotes are stripped from the result.

    The parser ignores YAML features we don't use (anchors,
    multi-line strings with `|`, etc.) — they're rare in our
    templates and adding full YAML support would pull in a
    dependency. If a deployment needs them, switch to PyYAML
    here; the public-API contract doesn't change.
    """
    out: dict[str, Any] = {}
    current_list_key: str | None = None
    current_dict_key: str | None = None
    current_dict: dict[str, Any] = {}

    for raw in block.splitlines():
        # Drop comments
        if "#" in raw:
            # Comments can be inline; preserve URLs by only stripping
            # comments preceded by whitespace
            raw = re.sub(r"\s+#.*$", "", raw)
        line = raw.rstrip()

        if not line.strip():
            continue

        # Block-list continuation: "  - item" or "- item"
        m = re.match(r"^\s+-\s+(.+)$", line)
        if m and current_list_key:
            val = _strip_quotes(m.group(1).strip())
            out.setdefault(current_list_key, []).append(val)
            continue

        # Nested-dict continuation: indented "  key: value"
        m = re.match(r"^\s{2,}(\w+)\s*:\s*(.*)$", line)
        if m and current_dict_key:
            k, v = m.group(1), m.group(2).strip()
            current_dict[k] = _coerce_value(v)
            out[current_dict_key] = current_dict
            continue

        # Top-level "key:" or "key: value"
        m = re.match(r"^(\w[\w_-]*)\s*:\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            current_list_key = None
            current_dict_key = None
            current_dict = {}

            if not val:
                # Could be the start of a block list or nested dict
                current_list_key = key
                current_dict_key = key
                continue

            # Inline list: "key: [a, b, c]"
            if val.startswith("[") and val.endswith("]"):
                items = [
                    _strip_quotes(s.strip())
                    for s in val[1:-1].split(",")
                    if s.strip()
                ]
                out[key] = items
                continue

            out[key] = _coerce_value(val)

    return out


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _coerce_value(s: str) -> Any:
    """Best-effort: int / float / bool / string. Strings are quote-stripped."""
    s = s.strip()
    if not s:
        return ""
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return _strip_quotes(s)


__all__ = [
    "parse_skill_frontmatter",
    "parse_script_metadata",
    "is_strategic_skill",
    "STRATEGIC_FRONTMATTER_KEYS",
]
