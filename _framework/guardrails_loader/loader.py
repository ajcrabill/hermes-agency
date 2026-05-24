# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
The actual Guardrails.md loader (enforcement-layer reader).

See `__init__.py` for the public-API contract.
"""

from __future__ import annotations

import re
from typing import Optional

from _framework.constants import GUARDRAILS_MD, VALUES_MD


def load_guardrails() -> str:
    """Return Guardrails.md as raw markdown.

    Falls back to Values.md if Guardrails.md doesn't exist yet —
    transitional during the v0.22.4-spec rename. Empty string if
    neither file is present.
    """
    if GUARDRAILS_MD.exists():
        return _safe_read(GUARDRAILS_MD)
    # Legacy fallback
    if VALUES_MD.exists():
        return _safe_read(VALUES_MD)
    return ""


def load_guardrails_parsed() -> Optional[dict]:
    """Best-effort parse of the three-layer structure.

    Returns:
        {
            "guardrails": [
                {
                    "title": "Work the Principal is proud of",
                    "statement": "The business will not ...",
                    "interim_guardrails": [
                        {
                            "title": "Engagement fit screen",
                            "statement": "...100% by March 2026.",
                            "initiative_refs": ["cos/values-fit-screen-prepper"],
                        },
                        ...
                    ],
                },
                ...
            ],
        }
        None if the file is absent.

    Parser is intentionally lenient — Guardrails.md is hand-edited
    markdown and won't always be perfectly structured. Callers
    should treat absent fields gracefully.
    """
    raw = load_guardrails()
    if not raw:
        return None

    guardrails: list[dict] = []
    current_guardrail: Optional[dict] = None
    current_interim: Optional[dict] = None
    next_line_is_statement = False
    statement_target: Optional[dict] = None

    for line in raw.splitlines():
        line = line.rstrip()

        # Guardrail heading: "### Guardrail 1 — Title"
        m = re.match(r"^###\s+Guardrail\s+\d+\s*[—–-]\s*(.+)$", line)
        if m:
            current_guardrail = {
                "title": m.group(1).strip(),
                "statement": "",
                "interim_guardrails": [],
            }
            guardrails.append(current_guardrail)
            current_interim = None
            next_line_is_statement = True
            statement_target = current_guardrail
            continue

        # Interim Guardrail heading: "**Interim Guardrail 1.1 — Title**"
        m = re.match(
            r"^\*\*Interim Guardrail\s+[\d.]+\s*[—–-]\s*(.+?)\*\*\s*$",
            line,
        )
        if m and current_guardrail is not None:
            current_interim = {
                "title": m.group(1).strip(),
                "statement": "",
                "initiative_refs": [],
            }
            current_guardrail["interim_guardrails"].append(current_interim)
            next_line_is_statement = True
            statement_target = current_interim
            continue

        # Initiative ref: "- skill: profile/skill-name" or "- script: ..."
        m = re.match(r"^-\s+(?:skill|script):\s+`?([^`*\s]+)`?", line)
        if m and current_interim is not None:
            current_interim["initiative_refs"].append(m.group(1).strip())
            continue

        # Statement line — captured right after a heading
        if next_line_is_statement and line and not line.startswith("#"):
            if statement_target is not None:
                statement_target["statement"] = line.strip()
            next_line_is_statement = False
            statement_target = None
            continue

        # Blank line between heading and statement — keep waiting
        if next_line_is_statement and not line:
            continue

        # Otherwise reset the statement-capture state
        if line.startswith("#") or line.startswith("---"):
            next_line_is_statement = False
            statement_target = None

    return {"guardrails": guardrails} if guardrails else None


def _safe_read(path) -> str:
    """Read text, returning empty string on any IO error."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


__all__ = ["load_guardrails", "load_guardrails_parsed"]
