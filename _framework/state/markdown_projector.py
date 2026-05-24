# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Markdown projector — DB → vault regeneration.

Solves the v7 "vault and DB drift" problem (Appendix A.4 of spec).
The DB is canonical; the markdown files in the vault are the
human-readable projection. When the DB changes, the framework can
regenerate the vault.

Two modes:

  - **Periodic** (default): every N minutes, project the DBs that have
    changed since last run. Cheap; no live hooks needed.
  - **On-demand**: `agency vault project [--db learning|kanban|...]`
    runs a single projection now.

Per-DB projectors live in `projectors/`. Each is a small function:
  `project(out_dir: Path) -> int` returning the number of files written.

The framework ships projectors for the DBs it owns:
  learning.db    → vault/learning/rules.md + per-skill firings.md
  goal_tracking.db → vault/goals/tracking.md
  finance.db     → vault/finance/{cash-flow.md, revenue.md, burn.md}
  prototypes.db  → vault/prototypes/<name>.md (one per prototype)

Operators can register additional projectors via
`register_projector(name, project_fn)`.

The output dir is `agency-vault/projections/` by default. Operators
can override per-projector.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from _framework.constants import AGENCY_VAULT, STATE_DIR


PROJECTIONS_DIR_DEFAULT = AGENCY_VAULT / "projections"


# ── Projector registry ─────────────────────────────────────────────────


_PROJECTORS: dict[str, Callable[[Path], int]] = {}


def register_projector(name: str, fn: Callable[[Path], int]) -> None:
    _PROJECTORS[name] = fn


def list_projectors() -> list[str]:
    return sorted(_PROJECTORS)


def project_all(out_root: Path | None = None) -> dict[str, int]:
    """Run every registered projector. Returns {name: file_count}."""
    out = out_root or PROJECTIONS_DIR_DEFAULT
    out.mkdir(parents=True, exist_ok=True)
    results: dict[str, int] = {}
    for name, fn in _PROJECTORS.items():
        sub = out / name
        sub.mkdir(parents=True, exist_ok=True)
        try:
            n = fn(sub)
            results[name] = n
        except Exception as e:
            results[name] = -1
            (sub / "_error.txt").write_text(f"projector failed: {e}\n", encoding="utf-8")
    _write_index(out, results)
    return results


def project_one(name: str, out_root: Path | None = None) -> int:
    if name not in _PROJECTORS:
        raise ValueError(f"unknown projector {name!r}; registered: {list_projectors()}")
    out = (out_root or PROJECTIONS_DIR_DEFAULT) / name
    out.mkdir(parents=True, exist_ok=True)
    return _PROJECTORS[name](out)


def _write_index(out_root: Path, results: dict[str, int]) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    lines = ["# projections — index", "", f"_Generated {ts}_", ""]
    for name, n in sorted(results.items()):
        lines.append(f"- `{name}/` — {n} file(s)")
    (out_root / "_index.md").write_text("\n".join(lines), encoding="utf-8")


# ── Built-in projectors ───────────────────────────────────────────────


def _project_learning(out: Path) -> int:
    """One rules.md file per skill (for grep-ability + git-tracking
    of rule corpus changes)."""
    from _framework.learning.learning_db import LEARNING_DB, decode_json_col
    if not LEARNING_DB.exists():
        return 0
    c = sqlite3.connect(str(LEARNING_DB))
    c.row_factory = sqlite3.Row
    try:
        rows = c.execute(
            "SELECT id, correction, skill_tags, role_tags, voice_tags, is_hard, "
            "status, source, created_at, notes FROM learning_rules "
            "WHERE status='active' ORDER BY created_at DESC"
        ).fetchall()
    finally:
        c.close()
    by_skill: dict[str, list[dict]] = {}
    for r in rows:
        for tag in decode_json_col(r["skill_tags"]) or ["general"]:
            by_skill.setdefault(tag, []).append(dict(r))
    files_written = 0
    for skill, items in by_skill.items():
        path = out / f"{skill}.md"
        lines = [f"# Learning rules — {skill}", "",
                 f"_Projected {datetime.now(timezone.utc).isoformat()}_", ""]
        for r in items:
            marker = "**HARD**" if r["is_hard"] else "•"
            roles = ", ".join(decode_json_col(r["role_tags"]))
            voice = ", ".join(decode_json_col(r["voice_tags"]))
            lines.append(f"- {marker} `{r['id']}` — {r['correction']}")
            meta = []
            if roles: meta.append(f"roles: {roles}")
            if voice: meta.append(f"voice: {voice}")
            meta.append(f"source: {r['source']}")
            meta.append(f"captured: {r['created_at']}")
            lines.append(f"  *({' · '.join(meta)})*")
        path.write_text("\n".join(lines), encoding="utf-8")
        files_written += 1
    return files_written


def _project_goals(out: Path) -> int:
    """One tracking.md showing each metric's current status + last 30d
    of observations."""
    from _framework.goals.tracking import GOAL_TRACKING_DB_DEFAULT
    from _framework.goals import list_metrics, metric_status, observation_history
    if not GOAL_TRACKING_DB_DEFAULT.exists():
        return 0
    metrics = list_metrics()
    if not metrics:
        return 0
    lines = ["# Goal tracking — projection",
             "",
             f"_Projected {datetime.now(timezone.utc).isoformat()}_", ""]
    for m in metrics:
        status = metric_status(m.id)
        history = observation_history(m.id, days=30)
        lines.append(f"## {m.metric_name}")
        lines.append("")
        lines.append(f"- Goal: {m.goal_text}")
        lines.append(f"- Target: {m.target_value} {m.unit} by {m.target_at or 'no deadline'}")
        lines.append(f"- Status: **{status['status']}** — {status.get('reason', '')}")
        if history:
            lines.append("- Recent observations:")
            for h in history[-8:]:
                lines.append(f"  - {h['observed_at']}: {h['value']}")
        lines.append("")
    (out / "tracking.md").write_text("\n".join(lines), encoding="utf-8")
    return 1


def _project_finance(out: Path) -> int:
    """Cash-flow + revenue + burn summary."""
    from _framework.finance.finance_db import FINANCE_DB_DEFAULT
    if not FINANCE_DB_DEFAULT.exists():
        return 0
    from _framework.finance import (
        list_invoices_in, list_invoices_out, list_expenses, list_revenue,
        revenue_by_source, monthly_burn,
    )
    ts = datetime.now(timezone.utc).isoformat()
    files = 0

    # Cash-flow snapshot
    burn = monthly_burn(months=3)
    rev_recent = list_revenue()[:20]
    cash_path = out / "cash-flow.md"
    cash_lines = [
        f"# Cash flow projection", "", f"_Projected {ts}_", "",
        f"## 3-month burn",
        "",
        f"- Total: ${burn['total_cents'] / 100:.2f}",
        f"- Monthly avg: ${burn['monthly_avg_cents'] / 100:.2f}",
        f"- Expense count: {burn['expense_count']}",
        "",
        f"## Recent revenue (last 20)", "",
    ]
    for r in rev_recent:
        cash_lines.append(
            f"- {r['received_at']}: ${r['amount_cents'] / 100:.2f} "
            f"from {r['client']} ({r['source']})"
        )
    cash_path.write_text("\n".join(cash_lines), encoding="utf-8")
    files += 1

    # Revenue attribution
    sources = revenue_by_source()
    rev_path = out / "revenue.md"
    rev_lines = [f"# Revenue attribution", "", f"_Projected {ts}_", "",
                 f"## By source", ""]
    total = sum(s["total_cents"] for s in sources)
    for s in sources:
        pct = s["total_cents"] / total * 100 if total else 0
        rev_lines.append(
            f"- **{s['source']}**: ${s['total_cents'] / 100:.2f} "
            f"({pct:.1f}%, {s['n']} payments)"
        )
    rev_path.write_text("\n".join(rev_lines), encoding="utf-8")
    files += 1

    # Outstanding invoices
    inv_lines = [f"# Invoices snapshot", "", f"_Projected {ts}_", "",
                 f"## Outstanding (us → clients)", ""]
    for inv in list_invoices_out(unpaid_only=True):
        inv_lines.append(
            f"- ${inv['amount_cents'] / 100:.2f} to {inv['client']} "
            f"due {inv['due_at']} (invoice #{inv['our_invoice_id'] or inv['id']})"
        )
    inv_lines.append("")
    inv_lines.append("## Outstanding (vendors → us)")
    inv_lines.append("")
    for inv in list_invoices_in(unpaid_only=True):
        inv_lines.append(
            f"- ${inv['amount_cents'] / 100:.2f} to {inv['vendor']} "
            f"due {inv['due_at']} ({inv['category']})"
        )
    (out / "invoices.md").write_text("\n".join(inv_lines), encoding="utf-8")
    files += 1

    return files


def _project_prototypes(out: Path) -> int:
    """One file per active prototype, full round history."""
    from _framework.prototyping.iteration import PROTOTYPE_DB_DEFAULT
    if not PROTOTYPE_DB_DEFAULT.exists():
        return 0
    from _framework.prototyping import list_prototypes, get_prototype
    protos = list_prototypes(status="active")
    files = 0
    for p in protos:
        full = get_prototype(p["id"])
        if not full:
            continue
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in p["name"])
        path = out / f"{safe}.md"
        ts = datetime.now(timezone.utc).isoformat()
        lines = [
            f"# Prototype: {p['name']}", "",
            f"_Projected {ts}_", "",
            f"- Profile: {p['profile']}",
            f"- Audience: {p['audience']}",
            f"- Purpose: {p['purpose']}",
            f"- Current round: {p['current_round']}",
            "",
            "## Rounds",
            "",
        ]
        for r in full.get("rounds", []):
            lines.append(f"### Round {r.round_number} — {r.created_at}")
            lines.append("")
            if r.feedback:
                lines.append(f"**Feedback ({r.feedback_source}):**")
                lines.append(r.feedback)
                lines.append("")
            if r.change_summary:
                lines.append(f"**Change:** {r.change_summary}")
                lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        files += 1
    return files


# Register the built-ins
register_projector("learning", _project_learning)
register_projector("goals", _project_goals)
register_projector("finance", _project_finance)
register_projector("prototypes", _project_prototypes)


__all__ = [
    "PROJECTIONS_DIR_DEFAULT",
    "register_projector", "list_projectors",
    "project_all", "project_one",
]
