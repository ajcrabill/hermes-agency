# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Quarterly strategic-review-prep core logic (v0.23.7).

Per StrategicPlanning.md §6.3, the top-tier review answers a
different question than the weekly health check:

  - Weekly: "are we implementing? are we deploying resources wisely?"
  - Quarterly: "do we have the *right* Outcomes?"

The packet aggregates 90 days of:

  - Health-check trend (proxied by current state + audit history)
  - Audit findings summary (counts per rule code)
  - Firings rollup (skill_tag → count, last 90d)
  - Three-layer plan summary (mission, Outcomes, IGs, Initiatives
    — with status flags)

It also contains a checklist of Principal-facing questions drawn
from StrategicPlanning.md §6.3:

  - Are these still the right Outcomes for this season?
  - Do the Interim Goals actually predict Outcome movement, or
    have we been measuring something that doesn't matter?
  - Are there Outcomes we're avoiding because they're
    uncomfortable to measure?
  - What pivots should we make to the layer-1 (Outcomes /
    Guardrails) structure?
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from _framework.constants import LEARNING_DB
from _framework.goals import read_goals_strategic


# ── Dataclass ──────────────────────────────────────────────────────────


@dataclass
class ReviewPacket:
    """The quarterly review packet."""

    generated_at: str
    quarter_label: str                          # "Q2 2026"
    period_start: str                           # ISO date
    period_end: str                             # ISO date
    has_strategic_plan: bool = False
    mission: str = ""
    plan_summary: list[dict] = field(default_factory=list)
    audit_findings_by_code: dict = field(default_factory=dict)
    audit_blocking_count: int = 0
    audit_total_count: int = 0
    firings_by_tag: dict = field(default_factory=dict)
    firings_total: int = 0
    principal_questions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ── Public API ──────────────────────────────────────────────────────────


def is_quarterly_trigger_day(when: date | None = None) -> bool:
    """True iff `when` (or today) is the first Monday of Jan / Apr /
    Jul / Oct.

    The CoS profile's weekly cron schedules a check; this function
    decides whether *this* week is a quarterly fire week.
    """
    d = when or date.today()
    if d.month not in (1, 4, 7, 10):
        return False
    if d.weekday() != 0:  # Monday == 0
        return False
    # First Monday: day number <= 7
    return d.day <= 7


def next_quarterly_trigger_date(after: date | None = None) -> date:
    """Return the next first-Monday-of-Jan/Apr/Jul/Oct after `after`
    (or today)."""
    d = (after or date.today()) + timedelta(days=1)
    while True:
        if is_quarterly_trigger_day(d):
            return d
        d += timedelta(days=1)


def produce_review_packet(
    *,
    learning_db: Path | None = None,
    now: datetime | None = None,
    period_days: int = 90,
) -> ReviewPacket:
    """Build the quarterly packet.

    Reads only — never mutates vault docs. The Principal-driven
    review meeting is the *next* step; this skill just hands the
    Principal a marked-up data summary.
    """
    now = now or datetime.now(timezone.utc)
    period_end = now.date()
    period_start = period_end - timedelta(days=period_days)

    packet = ReviewPacket(
        generated_at=now.isoformat(timespec="seconds"),
        quarter_label=_quarter_label(period_end),
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
    )

    # Strategic plan structure
    strategic = read_goals_strategic()
    if strategic is None:
        packet.notes.append(
            "No three-layer Goals.md found. The quarterly review "
            "requires a strategic plan to review against. Run "
            "`/agency setup` first."
        )
    else:
        packet.has_strategic_plan = True
        packet.mission = strategic.mission
        packet.plan_summary = _summarize_plan(strategic)

    # Audit findings
    try:
        packet.audit_findings_by_code, packet.audit_blocking_count, packet.audit_total_count = (
            _audit_summary()
        )
    except Exception as e:
        packet.notes.append(f"Audit skipped: {e}")

    # Firings rollup (last 90 days)
    try:
        packet.firings_by_tag, packet.firings_total = _firings_rollup(
            db_path=learning_db, since=period_start
        )
    except Exception as e:
        packet.notes.append(f"Firings rollup skipped: {e}")

    # Principal-facing questions
    packet.principal_questions = _principal_questions(packet)

    return packet


def render_packet(packet: ReviewPacket) -> str:
    """Render the packet as plain-language markdown for the Principal."""
    if not packet.has_strategic_plan:
        return (
            f"# Quarterly strategic review — {packet.quarter_label}\n\n"
            f"*Generated {packet.generated_at}*\n\n"
            "**No strategic plan to review.** Goals.md isn't in the "
            "three-layer (Outcomes → Interim Goals → Initiatives) "
            "format yet. Run `/agency setup` to start one.\n\n"
            + "\n".join(f"_Note: {n}_" for n in packet.notes)
        )

    lines = [
        f"# Quarterly strategic review — {packet.quarter_label}",
        "",
        f"*Generated {packet.generated_at} for the review meeting.*",
        f"*Period: {packet.period_start} → {packet.period_end}*",
        "",
        "_The review meeting is yours. This packet is the data side._",
        "_Walk in with these numbers + the questions at the bottom_",
        "_— decide whether the plan needs structural changes._",
        "",
    ]
    if packet.mission:
        lines.append(f"**Mission:** {packet.mission}")
        lines.append("")

    lines.append("## The plan (current state)")
    lines.append("")
    if not packet.plan_summary:
        lines.append("_No Outcomes defined yet._")
    else:
        for outcome in packet.plan_summary:
            lines.append(
                f"### Outcome {outcome['number']} — {outcome['title']}"
            )
            if outcome.get("statement"):
                lines.append(f"> {outcome['statement']}")
            lines.append("")
            if not outcome["interim_goals"]:
                lines.append("_No Interim Goals — this Outcome has no leading indicators._")
            for ig in outcome["interim_goals"]:
                init_count = len(ig["initiatives"])
                lines.append(
                    f"- **Interim Goal {ig['number']} — {ig['title']}** "
                    f"({init_count} Initiative{'s' if init_count != 1 else ''})"
                )
                if ig.get("statement"):
                    lines.append(f"  > {ig['statement']}")
                for ref in ig["initiatives"]:
                    firings = packet.firings_by_tag.get(
                        ref["path"].rsplit("/", 1)[-1], 0
                    )
                    lines.append(
                        f"  - `{ref['kind']}: {ref['path']}` — "
                        f"{firings} firings in last 90d"
                    )
            lines.append("")

    lines.append("## Activity (last 90 days)")
    lines.append("")
    lines.append(f"- Total firings: **{packet.firings_total}**")
    if packet.firings_by_tag:
        top = sorted(packet.firings_by_tag.items(), key=lambda kv: -kv[1])[:5]
        lines.append("- Most-active Initiatives:")
        for tag, n in top:
            lines.append(f"  - `{tag}` — {n} firings")
    else:
        lines.append("- No firings recorded.")
    lines.append("")

    lines.append("## Audit signals")
    lines.append("")
    if packet.audit_total_count == 0:
        lines.append("_Audit ran clean — no alignment findings._")
    else:
        lines.append(
            f"- **{packet.audit_total_count}** findings "
            f"({packet.audit_blocking_count} blocking)"
        )
        top_rules = sorted(
            packet.audit_findings_by_code.items(),
            key=lambda kv: -kv[1],
        )[:5]
        for code, count in top_rules:
            lines.append(f"  - `{code}`: {count}")
    lines.append("")

    lines.append("## Questions to bring to the review meeting")
    lines.append("")
    for q in packet.principal_questions:
        lines.append(f"- {q}")
    lines.append("")

    if packet.notes:
        lines.append("---")
        for n in packet.notes:
            lines.append(f"_Note: {n}_")
    return "\n".join(lines)


# ── Internals ──────────────────────────────────────────────────────────


def _quarter_label(d: date) -> str:
    q = ((d.month - 1) // 3) + 1
    return f"Q{q} {d.year}"


def _summarize_plan(strategic) -> list[dict]:
    """Walk the three-layer structure into a dict that's easy to
    render."""
    out = []
    for o in strategic.outcomes:
        ig_list = []
        for ig in o.interim_goals:
            ig_list.append({
                "number": ig.number,
                "title": ig.title,
                "statement": ig.statement,
                "initiatives": [
                    {"kind": r.kind, "path": r.path}
                    for r in ig.initiative_refs
                ],
            })
        out.append({
            "number": o.number,
            "title": o.title,
            "statement": o.statement,
            "interim_goals": ig_list,
        })
    return out


def _audit_summary() -> tuple[dict, int, int]:
    """Run audit + return (by_code, blocking_count, total_count)."""
    from _framework.audit import audit_deployment

    report = audit_deployment(strict=False)
    by_code: dict[str, int] = {}
    for f in report.findings:
        by_code[f.code] = by_code.get(f.code, 0) + 1
    blocking = sum(1 for f in report.findings if f.is_blocking)
    return by_code, blocking, len(report.findings)


def _firings_rollup(
    *, db_path: Path | None, since: date,
) -> tuple[dict, int]:
    """Aggregate firings by `skill_tag` since `since` (inclusive)."""
    db = db_path or LEARNING_DB
    if not db.exists():
        return {}, 0
    by_tag: dict[str, int] = {}
    total = 0
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT skill_tag, COUNT(*) AS n FROM firings "
                "WHERE created_at >= ? GROUP BY skill_tag",
                (since.isoformat(),),
            ).fetchall()
            for r in rows:
                by_tag[str(r["skill_tag"])] = int(r["n"])
                total += int(r["n"])
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return {}, 0
    return by_tag, total


def _principal_questions(packet: ReviewPacket) -> list[str]:
    """The standard quarterly questions, with one or two tailored
    based on what the data shows."""
    questions = [
        "Are these still the right Outcomes for this season of the "
        "business / life? (Not whether they're achievable — whether "
        "they're the *right destinations*.)",
        "For each Interim Goal: do you believe it actually predicts "
        "Outcome movement, or has it become a proxy that no longer "
        "tracks the real thing?",
        "Are there Outcomes you've been avoiding because they're "
        "uncomfortable to measure? (Health, relationships, financial "
        "vulnerability, etc.)",
        "What did the past 90 days teach you that the plan didn't "
        "anticipate? Should a new Outcome be added, or one retired?",
        "Of the layer-1 (Outcomes / Guardrails) decisions — is there "
        "one that the CoS should bring forward as a refinement "
        "proposal in the kanban?",
    ]
    # Data-tailored
    if packet.firings_total == 0:
        questions.append(
            "The system recorded zero firings this quarter. Is this "
            "because the work isn't happening, or because it isn't "
            "being logged? Either way is worth diagnosing."
        )
    if packet.audit_blocking_count > 0:
        questions.append(
            f"The audit shows {packet.audit_blocking_count} blocking "
            f"alignment finding(s). At least one of these should "
            f"resolve before next quarter starts."
        )
    return questions


__all__ = [
    "ReviewPacket",
    "produce_review_packet",
    "render_packet",
    "is_quarterly_trigger_day",
    "next_quarterly_trigger_date",
]
