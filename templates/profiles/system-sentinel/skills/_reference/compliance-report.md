---
skill_id: compliance-report
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic]
---

# Compliance report

Sunday 06:00 — generates the weekly learning-loop health digest.
Captures captured, fired, recaptured. Surfaces dead rules and broken
skills.

## What this skill does

Calls `_framework.learning.compliance_report.weekly_compliance_report()`:

1. Counts rules captured this week
2. Top 8 most-fired rules + their override rate
3. Recapture events this week (each is a system-failure flag)
4. Rules never fired in 90 days (dead or mis-tagged)
5. Top 5 active skills (firings count, last 30d)
6. Top 5 broken skills (>3 rules, 0 firings in 30d)

Renders as markdown. Files as a kanban task `tenant=compliance` so
the operator reads it as part of weekly review.

## Inputs

- `learning.db` (read-only)

## Supervised learning

Rules tagged `role:system-sentinel`. Particularly: thresholds for
what to surface.

## Action surface

- (read-only) — file kanban task with report body, emit event

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{EVENTS_DB}}"
      query: "SELECT * FROM events WHERE kind='compliance_report_generated' AND ts >= datetime('now', '-2 hour')"
      expect_min: 1
```

## Failure modes

- **Empty learning corpus** — no rules captured yet. Report says so
  clearly rather than rendering empty sections.
- **Report too long** — many broken skills. Truncate to top 5 in
  each category; full data in attached audit JSON.

## Self-check

1. Did I emit my heartbeat?
2. Did the report tie back to the seven-step loop (capture / fire /
   recapture / etc.)?
3. Are the broken-skill flags actionable?
