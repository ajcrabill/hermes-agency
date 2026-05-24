# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
operational-state.md + conversation-journal.md read/write helpers.

These files are markdown. The reader returns the raw text; the
writer appends to a named section (creating the section if absent).
Pruning takes lines older than N days and moves them to an archive
subdirectory.

Section format: `## <Section Name>\\n...content...\\n` — i.e. H2
headings. The append helper finds the H2 heading by exact match and
appends a timestamped block below it, before any subsequent H2.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import (
    CONVERSATION_JOURNAL_MD,
    OPERATIONAL_STATE_MD,
    STATE_VAULT,
)


def init_state_vault() -> None:
    """Ensure the state vault directory exists. File creation happens via
    the Tier 3 interview's `_state_files.ensure_initial_state_files`."""
    STATE_VAULT.mkdir(parents=True, exist_ok=True)
    (STATE_VAULT / "archive").mkdir(exist_ok=True)


def read_operational_state() -> str:
    if not OPERATIONAL_STATE_MD.exists():
        return ""
    return OPERATIONAL_STATE_MD.read_text(encoding="utf-8")


def read_conversation_journal() -> str:
    if not CONVERSATION_JOURNAL_MD.exists():
        return ""
    return CONVERSATION_JOURNAL_MD.read_text(encoding="utf-8")


def append_to_section(file_path: Path | str, section: str, body: str, *, actor: str = "") -> None:
    """Append a timestamped block under `## <section>` in the markdown file.

    Creates the section if missing (appends to end of file with a new H2).
    """
    p = Path(file_path).expanduser()
    init_state_vault()
    if not p.exists():
        p.write_text(f"# {p.stem}\n\n", encoding="utf-8")

    text = p.read_text(encoding="utf-8")
    timestamp = datetime.now(timezone.utc).isoformat()
    actor_tag = f" — {actor}" if actor else ""
    entry = f"\n_{timestamp}{actor_tag}_\n\n{body.rstrip()}\n"

    section_header = f"## {section}"

    if section_header in text:
        # Insert just before the NEXT H2 (or at end of file if section is last)
        idx = text.index(section_header)
        # Find the end of this section (next "## " at start of line, or EOF)
        rest = text[idx + len(section_header):]
        next_h2 = rest.find("\n## ")
        if next_h2 == -1:
            # Append at end of file
            new_text = text.rstrip() + "\n" + entry + "\n"
        else:
            insert_at = idx + len(section_header) + next_h2
            new_text = text[:insert_at] + entry + text[insert_at:]
    else:
        # Create the section
        new_text = text.rstrip() + f"\n\n{section_header}\n{entry}\n"

    p.write_text(new_text, encoding="utf-8")


def prune(file_path: Path | str, older_than_days: int = 90) -> dict:
    """Move entries older than `older_than_days` to the archive directory.

    For markdown files, we look for `_<ISO-timestamp>_` markers (the
    `_<timestamp>_` lines our appender writes). Entries older than
    cutoff are extracted into an archive file.

    Returns {moved: int, archive_path: str}.
    """
    import re

    p = Path(file_path).expanduser()
    if not p.exists():
        return {"moved": 0, "archive_path": ""}
    text = p.read_text(encoding="utf-8")
    cutoff = datetime.now(timezone.utc).timestamp() - older_than_days * 86400

    # Find blocks: each starts with `_<ISO ts>_` line, ends at next `_<ISO ts>_` or `## ` or EOF.
    ts_re = re.compile(r"^_(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^_\n]*)_(.*)$", re.M)
    matches = list(ts_re.finditer(text))
    if not matches:
        return {"moved": 0, "archive_path": ""}

    moved: list[tuple[str, str]] = []
    kept_text = text
    # Walk in reverse so removal indices stay valid
    for m in reversed(matches):
        ts_str = m.group(1)
        try:
            ts_dt = datetime.fromisoformat(ts_str).timestamp()
        except Exception:
            continue
        if ts_dt >= cutoff:
            continue
        # Block ends at next ts marker or `## ` or EOF
        end = len(kept_text)
        rest_after = kept_text[m.end():]
        next_ts = ts_re.search(rest_after)
        next_h2 = rest_after.find("\n## ")
        candidates = [c for c in (next_ts.start() if next_ts else None, next_h2 if next_h2 >= 0 else None) if c is not None]
        if candidates:
            end = m.end() + min(candidates)
        block = kept_text[m.start():end]
        kept_text = kept_text[:m.start()] + kept_text[end:]
        moved.append((ts_str, block))

    if not moved:
        return {"moved": 0, "archive_path": ""}

    archive_dir = STATE_VAULT / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{p.stem}-{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(archive_path, "a", encoding="utf-8") as f:
        for ts, block in reversed(moved):
            f.write(block)
            if not block.endswith("\n"):
                f.write("\n")

    p.write_text(kept_text, encoding="utf-8")
    return {"moved": len(moved), "archive_path": str(archive_path)}


__all__ = [
    "init_state_vault",
    "read_operational_state",
    "read_conversation_journal",
    "append_to_section",
    "prune",
]
