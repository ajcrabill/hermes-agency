# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Weekly compliance report — Sunday morning learning-loop health summary.

Produces a structured digest of:
  - rules captured this week (count + sample)
  - rules fired most (top 8 + override rate)
  - re-capture events (each is a system-failure flag)
  - rules never fired in 90 days (likely dead or mis-tagged)
  - top 5 skills by firings count (where the loop is most active)
  - top 5 skills with >3 rules and 0 firings (where the loop may be broken)

Delivered as a kanban task to the owner (tenant=compliance). Sentinel
authors it via her `compliance-report` cron (§5.3 of spec).

The report is intentionally human-formatted markdown — the kanban
plugin renders it as the task body, and the owner reads it Sunday
morning without needing to query the DB themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .learning_db import decode_json_col, get_db


@dataclass
class ComplianceReport:
    generated_at: str
    rules_captured_this_week: int
    sample_recent_corrections: list[dict] = field(default_factory=list)
    top_firing_rules: list[dict] = field(default_factory=list)
    recapture_events: list[dict] = field(default_factory=list)
    dead_rules: list[dict] = field(default_factory=list)
    top_skills_active: list[tuple[str, int]] = field(default_factory=list)
    top_skills_broken: list[tuple[str, int]] = field(default_factory=list)

    def to_markdown(self) -> str:
        gen = self.generated_at
        sections = [
            "# Weekly compliance report",
            "",
            f"_Generated: {gen}_",
            "",
            "Learning-loop health for the past week. The bar to clear: corrections get captured, propagate to the right skills, and shape behavior — without the owner repeating themselves.",
            "",
        ]
        sections += [
            "## Capture",
            "",
            f"- **{self.rules_captured_this_week}** corrections captured this week.",
        ]
        if self.sample_recent_corrections:
            sections.append("")
            sections.append("Recent (most recent first):")
            sections.append("")
            for r in self.sample_recent_corrections[:5]:
                tags = ", ".join(decode_json_col(r.get("skill_tags")))
                sections.append(f"- `{r['id']}` — {r['correction'][:140]}  *(skills: {tags})*")
        sections.append("")

        sections += ["## Firing (loop closed)", ""]
        if self.top_firing_rules:
            sections.append("Top 8 most-fired rules in the last 30 days:")
            sections.append("")
            for r in self.top_firing_rules:
                hard = " (HARD)" if r.get("is_hard") else ""
                override = f"  · override rate {r.get('override_rate', 0):.0%}" if r.get("is_hard") else ""
                sections.append(
                    f"- `{r['id']}` — fired {r['firing_count']}x{hard}{override} — {r['correction'][:100]}"
                )
        else:
            sections.append("_No firings recorded this week._ The loop may be broken — check that skills are recording firings.")
        sections.append("")

        sections += ["## Recapture (loop broken)", ""]
        if self.recapture_events:
            sections.append(f"**⚠ {len(self.recapture_events)} recapture event(s)** — the owner corrected something we'd already been corrected on.")
            sections.append("")
            for ev in self.recapture_events:
                sections.append(
                    f"- new rule `{ev['new_rule_id']}` is {ev['similarity']:.0%} similar to prior rule `{ev['similar_to']}` (skills: {ev['skill_tags']})"
                )
            sections.append("")
            sections.append("Each row above is a system-failure flag. Investigate the injection chain for the implicated skill(s).")
        else:
            sections.append("✓ No recapture events. The loop closed clean.")
        sections.append("")

        sections += ["## Dead / mis-tagged rules", ""]
        if self.dead_rules:
            sections.append(f"{len(self.dead_rules)} rule(s) never fired in 90 days. Candidates for re-tag, supersede, or remove:")
            sections.append("")
            for r in self.dead_rules[:10]:
                tags = ", ".join(decode_json_col(r.get("skill_tags")))
                sections.append(f"- `{r['id']}` — {r['correction'][:100]}  *(skills: {tags})*")
        else:
            sections.append("✓ Every active rule has fired at least once in 90 days.")
        sections.append("")

        sections += ["## Skill activity", ""]
        if self.top_skills_active:
            sections.append("Most-active skills (firings, last 30d):")
            sections.append("")
            for skill, n in self.top_skills_active:
                sections.append(f"- {skill}: {n}")
        sections.append("")
        if self.top_skills_broken:
            sections.append("Skills with >3 captured rules and 0 firings (loop likely broken):")
            sections.append("")
            for skill, n in self.top_skills_broken:
                sections.append(f"- {skill}: {n} rules, 0 firings")
        sections.append("")

        return "\n".join(sections)


def generate(days_window: int = 7, dead_days: int = 90, db_path=None) -> ComplianceReport:
    """Compute the weekly compliance report. Pure read; no side effects."""
    db = get_db(path=db_path)
    try:
        now = datetime.now(timezone.utc)
        week_ago = (now - timedelta(days=days_window)).isoformat()
        days_30_ago = (now - timedelta(days=30)).isoformat()
        dead_cutoff = (now - timedelta(days=dead_days)).isoformat()

        # Captured this week
        cap_rows = db.execute(
            "SELECT id, correction, skill_tags, created_at FROM learning_rules "
            "WHERE created_at >= ? AND status='active' ORDER BY created_at DESC",
            (week_ago,),
        ).fetchall()
        captured = len(cap_rows)
        sample = [dict(r) for r in cap_rows[:5]]

        # Top firing rules (last 30 days)
        top_firing_rows = db.execute(
            """
            SELECT lr.id, lr.correction, lr.is_hard,
                   COUNT(f.id) AS firing_count,
                   SUM(f.was_overridden) AS override_count
            FROM learning_rules lr
            JOIN firings f ON f.rule_id = lr.id
            WHERE f.created_at >= ?
            GROUP BY lr.id
            ORDER BY firing_count DESC
            LIMIT 8
            """,
            (days_30_ago,),
        ).fetchall()
        top_firing = []
        for r in top_firing_rows:
            d = dict(r)
            n = int(d["firing_count"])
            o = int(d["override_count"] or 0)
            d["override_rate"] = (o / n) if n > 0 else 0.0
            top_firing.append(d)

        # Recapture events this week (not dismissed)
        rc_rows = db.execute(
            "SELECT new_rule_id, similar_to, similarity, skill_tags, detected_at "
            "FROM recapture_events WHERE detected_at >= ? AND dismissed=0 "
            "ORDER BY detected_at DESC",
            (week_ago,),
        ).fetchall()
        recaptures = [dict(r) for r in rc_rows]

        # Dead rules (never fired in 90d, captured before cutoff)
        dead_rows = db.execute(
            """
            SELECT lr.id, lr.correction, lr.skill_tags, lr.created_at
            FROM learning_rules lr
            WHERE lr.status = 'active'
              AND lr.created_at < ?
              AND NOT EXISTS (SELECT 1 FROM firings f WHERE f.rule_id = lr.id AND f.created_at >= ?)
            ORDER BY lr.created_at ASC
            LIMIT 50
            """,
            (dead_cutoff, dead_cutoff),
        ).fetchall()
        dead = [dict(r) for r in dead_rows]

        # Top skills by firing count (last 30 days)
        active_rows = db.execute(
            "SELECT skill_tag, COUNT(*) AS n FROM firings WHERE created_at >= ? "
            "GROUP BY skill_tag ORDER BY n DESC LIMIT 5",
            (days_30_ago,),
        ).fetchall()
        top_active = [(r["skill_tag"], int(r["n"])) for r in active_rows]

        # Skills with >3 captured rules and 0 firings in 30 days (loop broken)
        # Note: skill_tags is a JSON array; we expand via a join workaround.
        # For v0.1 simplicity we scan in Python.
        all_rules = db.execute(
            "SELECT id, skill_tags FROM learning_rules WHERE status='active'"
        ).fetchall()
        skill_rule_count: dict[str, int] = {}
        for r in all_rules:
            for tag in decode_json_col(r["skill_tags"]):
                if tag == "general":
                    continue
                skill_rule_count[tag] = skill_rule_count.get(tag, 0) + 1

        skills_with_recent_firings = {r["skill_tag"] for r in active_rows}
        firing_rows_30d = db.execute(
            "SELECT DISTINCT skill_tag FROM firings WHERE created_at >= ?",
            (days_30_ago,),
        ).fetchall()
        skills_with_recent_firings.update(r["skill_tag"] for r in firing_rows_30d)

        broken = [
            (skill, n)
            for skill, n in skill_rule_count.items()
            if n > 3 and skill not in skills_with_recent_firings
        ]
        broken.sort(key=lambda x: -x[1])
        top_broken = broken[:5]

        return ComplianceReport(
            generated_at=now.isoformat(),
            rules_captured_this_week=captured,
            sample_recent_corrections=sample,
            top_firing_rules=top_firing,
            recapture_events=recaptures,
            dead_rules=dead,
            top_skills_active=top_active,
            top_skills_broken=top_broken,
        )
    finally:
        db.close()


def weekly_compliance_report(**kwargs) -> str:
    """Convenience: generate + render to markdown."""
    return generate(**kwargs).to_markdown()


__all__ = ["ComplianceReport", "generate", "weekly_compliance_report"]
