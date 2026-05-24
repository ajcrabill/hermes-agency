# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Strategic-plan health check core logic (v0.23.6).

Reads:

  - Goals.md (three-layer) via `read_goals_strategic()`
  - goal-tracking DB metric statuses (Interim Goal metrics)
  - learning-rules firings (Initiative cadence proxy)
  - audit findings (strategic-alignment rules from v0.23.3)

Produces a `HealthReport` with three structured layers — one
`OutcomeHealth` per Outcome (containing `InterimGoalHealth` per
Interim Goal, containing `InitiativeHealth` per Initiative ref).

Each level carries a status verdict:

  - "on-track"     — data shows healthy movement
  - "no-data"      — metric or firings not recorded yet
  - "at-risk"      — slipping; pivot worth considering
  - "missed"       — past target; pivot now
  - "drift"        — Initiative not firing at expected cadence

A *pivot proposal* is the point. After the structural data is
assembled, `_propose_pivots()` picks the two or three most pressing
drift signals and frames them as plain-language pivot suggestions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from _framework.constants import LEARNING_DB
from _framework.goals import (
    StrategicGoals, InitiativeRef, read_goals_strategic,
    metric_status, list_metrics, GoalMetric,
)


# ── Dataclasses ────────────────────────────────────────────────────────


@dataclass
class InitiativeHealth:
    """One Initiative (skill or script)'s recent activity."""

    ref: InitiativeRef
    firings_30d: int = 0
    last_firing_at: str = ""             # ISO-8601 or ""
    status: str = "no-data"              # on-track | drift | no-data
    note: str = ""                        # human-readable detail


@dataclass
class InterimGoalHealth:
    """One Interim Goal's SMART-metric status + Initiative rollup."""

    number: str                            # "1.1"
    title: str
    statement: str
    metric_status: str = "no-data"         # on-track | at-risk | missed | done | no-data
    metric_detail: str = ""                # e.g. "5 → 7 of 9; was 5 in Jan"
    initiatives: list[InitiativeHealth] = field(default_factory=list)

    @property
    def has_strategic_drift(self) -> bool:
        return self.metric_status in {"at-risk", "missed"} or any(
            i.status == "drift" for i in self.initiatives
        )


@dataclass
class OutcomeHealth:
    """One Outcome's overall health — rolled up from its Interim Goals."""

    number: int
    title: str
    statement: str
    interim_goals: list[InterimGoalHealth] = field(default_factory=list)
    lagging_indicator_note: str = (
        "Lagging-indicator data not yet collected at this layer. "
        "The Interim Goals (below) are the leading indicators."
    )

    @property
    def rolled_up_status(self) -> str:
        """If any Interim Goal is missed → outcome at risk; if any
        at-risk → at risk; otherwise on-track or no-data."""
        statuses = [ig.metric_status for ig in self.interim_goals]
        if "missed" in statuses:
            return "at-risk"
        if "at-risk" in statuses:
            return "at-risk"
        if all(s == "done" for s in statuses) and statuses:
            return "done"
        if all(s == "no-data" for s in statuses) and statuses:
            return "no-data"
        return "on-track"


@dataclass
class HealthReport:
    """The top-level weekly health check."""

    generated_at: str
    has_strategic_plan: bool                  # False if Goals.md not three-layer
    outcomes: list[OutcomeHealth] = field(default_factory=list)
    audit_finding_count: int = 0
    audit_blocking_count: int = 0
    audit_notes: list[str] = field(default_factory=list)
    pivot_proposals: list[str] = field(default_factory=list)
    mission: str = ""


# ── Public API ──────────────────────────────────────────────────────────


def run_health_check(
    *,
    learning_db: Path | None = None,
    tracking_db: Path | None = None,
    include_audit: bool = True,
    now: datetime | None = None,
) -> HealthReport:
    """Assemble the weekly health-check report.

    Reads only — never mutates Goals.md or any other vault file. The
    audit step is optional (the audit's own findings-only semantics
    mean it's safe to call, but tests can skip it for speed).
    """
    now = now or datetime.now(timezone.utc)
    report = HealthReport(
        generated_at=now.isoformat(timespec="seconds"),
        has_strategic_plan=False,
    )

    strategic = read_goals_strategic()
    if strategic is None:
        report.audit_notes.append(
            "Goals.md not in three-layer strategic format. Run `/agency "
            "setup` (or migrate) to build the strategic plan."
        )
        return report

    report.has_strategic_plan = True
    report.mission = strategic.mission

    # Index metrics by Interim Goal number (e.g. "1.1") — that's how
    # the audit + tracking modules tie a metric to its Interim Goal.
    metric_by_ig = _index_metrics_by_interim_goal(tracking_db)

    for outcome in strategic.outcomes:
        oh = OutcomeHealth(
            number=outcome.number,
            title=outcome.title,
            statement=outcome.statement,
        )
        for ig in outcome.interim_goals:
            igh = InterimGoalHealth(
                number=ig.number,
                title=ig.title,
                statement=ig.statement,
            )
            # Metric status (if a metric is registered for this IG)
            metric = metric_by_ig.get(ig.number)
            if metric is not None:
                try:
                    ms = metric_status(metric.id, db_path=tracking_db)
                    igh.metric_status = ms.get("status", "no-data")
                    igh.metric_detail = _format_metric_detail(ms)
                except Exception as e:
                    igh.metric_status = "no-data"
                    igh.metric_detail = f"(error reading metric: {e})"
            # Initiative firings
            for ref in ig.initiative_refs:
                ih = _check_initiative_health(
                    ref, learning_db=learning_db, now=now
                )
                igh.initiatives.append(ih)
            oh.interim_goals.append(igh)
        report.outcomes.append(oh)

    if include_audit:
        try:
            report.audit_finding_count, report.audit_blocking_count = (
                _run_audit_summary()
            )
        except Exception as e:
            report.audit_notes.append(f"Audit skipped: {e}")

    report.pivot_proposals = _propose_pivots(report)

    return report


def render_report(report: HealthReport) -> str:
    """Render the report as plain-language markdown.

    The goal: <60 seconds to read, names what's drifted, proposes pivots.
    """
    if not report.has_strategic_plan:
        return (
            "# Weekly strategic-plan health check\n\n"
            f"*Generated {report.generated_at}*\n\n"
            "**No strategic plan to check.** Goals.md isn't in the "
            "three-layer (Outcomes → Interim Goals → Initiatives) "
            "format yet. Run `/agency setup` to start one.\n\n"
            + "\n".join(f"- {n}" for n in report.audit_notes)
        )

    lines = [
        "# Weekly strategic-plan health check",
        "",
        f"*Generated {report.generated_at}*",
        "",
    ]
    if report.mission:
        lines.append(f"**Mission:** {report.mission}")
        lines.append("")

    # Pivot proposals come first — that's the point of the report
    if report.pivot_proposals:
        lines.append("## Pivots worth considering this week")
        lines.append("")
        for p in report.pivot_proposals:
            lines.append(f"- {p}")
        lines.append("")
    else:
        lines.append(
            "## Pivots worth considering this week\n\n"
            "*Nothing pressing. The plan is on track at every measured "
            "layer.*\n"
        )

    # Layer-by-layer detail
    lines.append("## Outcomes")
    lines.append("")
    for oh in report.outcomes:
        lines.append(
            f"### Outcome {oh.number} — {oh.title} "
            f"*({oh.rolled_up_status})*"
        )
        lines.append("")
        if oh.statement:
            lines.append(f"> {oh.statement}")
            lines.append("")
        lines.append(f"_{oh.lagging_indicator_note}_")
        lines.append("")
        for igh in oh.interim_goals:
            lines.append(
                f"**Interim Goal {igh.number} — {igh.title}** "
                f"*({igh.metric_status})*"
            )
            if igh.metric_detail:
                lines.append(f"  — {igh.metric_detail}")
            for ih in igh.initiatives:
                lines.append(
                    f"    - `{ih.ref.kind}: {ih.ref.path}` — "
                    f"{ih.firings_30d} firings in last 30d "
                    f"({ih.status})"
                )
            lines.append("")

    if report.audit_finding_count:
        lines.append(
            f"## Audit findings\n\n"
            f"{report.audit_blocking_count} blocking, "
            f"{report.audit_finding_count - report.audit_blocking_count} "
            f"informational. Run `/agency audit` to see detail.\n"
        )
    if report.audit_notes:
        lines.append("\n".join(f"_Note: {n}_" for n in report.audit_notes))

    return "\n".join(lines)


# ── Internals ──────────────────────────────────────────────────────────


def _index_metrics_by_interim_goal(
    tracking_db: Path | None,
) -> dict[str, GoalMetric]:
    """Return a `{interim_goal_number: GoalMetric}` map.

    Convention: a metric's `tag_interim_goal` column (or, when absent,
    the metric's name prefix like "1.1 ...") ties it to an Interim
    Goal. The tracking module has no schema-level IG link yet (v0.22
    flat goals); v0.23 uses a name-prefix convention.
    """
    out: dict[str, GoalMetric] = {}
    try:
        metrics = list_metrics(db_path=tracking_db)
    except Exception:
        return out
    for m in metrics:
        # Convention: either `metric_name` OR `goal_text` starts with
        # "<ig-number> " (e.g. "1.1 Active engagements"). We check
        # both — operators may put the IG number in either column.
        for candidate in (m.metric_name, m.goal_text):
            if not candidate:
                continue
            prefix = candidate.split(" ", 1)[0]
            if prefix and _looks_like_ig_number(prefix):
                out[prefix] = m
                break
    return out


def _looks_like_ig_number(s: str) -> bool:
    parts = s.split(".")
    return len(parts) == 2 and all(p.isdigit() for p in parts)


def _format_metric_detail(ms: dict) -> str:
    """One-line plain-language summary of a metric_status dict."""
    status = ms.get("status", "")
    if status == "no-data":
        return "no observations recorded yet"
    if status == "no-target":
        return "no target defined yet"
    reason = ms.get("reason", "")
    if reason:
        return reason
    cur = ms.get("latest_value")
    target = ms.get("target_value")
    if cur is None or target is None:
        return status
    return f"latest: {cur}; target: {target}"


def _check_initiative_health(
    ref: InitiativeRef,
    *,
    learning_db: Path | None,
    now: datetime,
) -> InitiativeHealth:
    """Count firings tagged with this Initiative's path in the last
    30 days. Skills' firings are tagged by `skill_tag = <skill-id>`
    where `<skill-id>` is the bare skill name (e.g.
    `lookalike-prospect-builder`, not `devon/lookalike-prospect-builder`).

    Both forms are checked.
    """
    ih = InitiativeHealth(ref=ref)
    db_path = learning_db or LEARNING_DB
    if not db_path.exists():
        ih.status = "no-data"
        ih.note = "learning DB not initialized"
        return ih

    # Skills: tag is the bare name. Scripts: kind=script, tag is the
    # filename (e.g. `pipeline-watchdog.py`).
    bare = ref.path.rsplit("/", 1)[-1]
    tags = {ref.path, bare}
    if ref.kind == "script" and bare.endswith(".py"):
        tags.add(bare[:-3])  # strip .py

    since = (now - timedelta(days=30)).isoformat(timespec="seconds")
    placeholders = ",".join("?" for _ in tags)
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                f"SELECT COUNT(*) AS n, MAX(created_at) AS last_at "
                f"FROM firings WHERE created_at >= ? AND skill_tag IN ({placeholders})",
                (since, *tags),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        ih.status = "no-data"
        ih.note = f"firings query error: {e}"
        return ih

    ih.firings_30d = int(row["n"] or 0)
    ih.last_firing_at = row["last_at"] or ""
    if ih.firings_30d == 0:
        ih.status = "drift"
        ih.note = "no firings in last 30 days"
    elif ih.firings_30d < 2:
        ih.status = "drift"
        ih.note = (
            "very low cadence — strategic skills typically fire weekly"
        )
    else:
        ih.status = "on-track"
    return ih


def _run_audit_summary() -> tuple[int, int]:
    """Return (total_finding_count, blocking_count) from the
    strategic-alignment audit rules."""
    from _framework.audit import audit_deployment

    report = audit_deployment(strict=False)
    blocking = sum(1 for f in report.findings if f.is_blocking)
    return len(report.findings), blocking


def _propose_pivots(report: HealthReport) -> list[str]:
    """Pick the 2-3 most pressing drift signals and frame each as
    a plain-language pivot proposal.

    Priority order:
      1. Any Interim Goal in `missed` status
      2. Any Interim Goal in `at-risk` status
      3. Any Initiative in `drift` status (no firings or very low)
      4. Outcomes with no measurable Interim Goals at all
    """
    proposals: list[str] = []

    # Missed metrics first
    for oh in report.outcomes:
        for igh in oh.interim_goals:
            if igh.metric_status == "missed":
                proposals.append(
                    f"**Interim Goal {igh.number} ({igh.title})** has "
                    f"missed its target. Either revise the SMART metric "
                    f"to one that's achievable, or change the "
                    f"Initiatives serving it. {igh.metric_detail}"
                )

    # At-risk next
    for oh in report.outcomes:
        for igh in oh.interim_goals:
            if igh.metric_status == "at-risk":
                proposals.append(
                    f"**Interim Goal {igh.number} ({igh.title})** is "
                    f"slipping. Consider what an additional Initiative "
                    f"would look like, or whether one of the existing "
                    f"Initiatives is the wrong shape."
                )

    # Drifting Initiatives — only mention if metric isn't already
    # flagged at the IG level (avoid double-mentioning)
    for oh in report.outcomes:
        for igh in oh.interim_goals:
            if igh.metric_status in ("missed", "at-risk"):
                continue
            for ih in igh.initiatives:
                if ih.status == "drift":
                    proposals.append(
                        f"`{ih.ref.kind}: {ih.ref.path}` (serving IG "
                        f"{igh.number}) {ih.note}. Either retire it or "
                        f"diagnose why it isn't firing."
                    )
                    break  # one per IG is plenty

    # Outcomes with no Interim Goals at all
    for oh in report.outcomes:
        if not oh.interim_goals:
            proposals.append(
                f"**Outcome {oh.number} ({oh.title})** has no Interim "
                f"Goals declared. Either draft Interim Goals + "
                f"Initiatives to serve it, or remove the Outcome."
            )

    # Cap at 3 — the report is supposed to be a pivot prompt, not a list
    return proposals[:3]


__all__ = [
    "HealthReport",
    "OutcomeHealth",
    "InterimGoalHealth",
    "InitiativeHealth",
    "run_health_check",
    "render_report",
]
