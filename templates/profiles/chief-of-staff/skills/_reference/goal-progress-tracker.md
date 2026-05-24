---
skill_id: goal-progress-tracker
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise, direct]
---

# Goal progress tracker

The "are we actually making progress?" skill. SMART goals are
measurable + time-bound by definition; this skill captures the
measurements, tracks them over time, and reports weekly on
on-track / at-risk / missed status per metric.

Pairs with:
- `smart-goal-coach` — defines what to track (the SMART goal +
  interim milestones)
- `time-use-analyzer` — measures whether time goes to the goals
- `weekly-brainstorm` — proposes new ways to move forward

## What this skill does

Three flows:

### Flow 1 — Set up tracking for a goal

For each annual goal in `Goals.md`, walk through Q&A with
{{OWNER_NAME}}:

1. "What's the measurable signal for this goal?" — e.g. "number of
   signed clients" / "newsletter open-rate" / "MRR in USD"
2. "What's the target value + deadline?" (these come from the SMART
   check; surfaced for confirmation)
3. "Where does the data come from?" — operator describes:
   - **Auto-sourced**: `crm.leads WHERE status='converted'`,
     `finance.revenue WHERE source='bd-outreach'`, etc. The skill
     wires the query.
   - **Manual**: operator records observations weekly. The skill
     reminds them.
4. The metric is recorded via `_framework.goals.define_metric()`.

### Flow 2 — Record observations

Weekly (or whenever data is available):

- **Auto-sourced metrics**: skill runs the configured query +
  records the value via `record_observation()`.
- **Manual metrics**: skill prompts {{OWNER_NAME}} via kanban task
  "Record this week's value for: <metric_name> (target was N by
  <date>; latest was M)".

### Flow 3 — Weekly status report

Every Sunday (folds into `weekly-review`):

For each tracked metric, compute via `metric_status()`:
- Current value vs target_value (% achieved)
- Days remaining until deadline
- Expected pace (% you'd be at if you were on linear pace)
- **Status verdict**: on-track / at-risk / missed / done /
  no-data / no-target

Render a report grouped by goal, sorted with at-risk + missed
first (so they get attention, not buried under wins).

## Inputs

- `Goals.md` — source of truth for goals + interim milestones
- The CRM / finance / kanban DBs — for auto-sourced metrics
- {{OWNER_NAME}}'s manual inputs for unautomatable metrics

## Supervised learning

Rules tagged `goal-progress-tracker`, `general`,
`role:chief-of-staff`. Per-operator calibration: which metrics
make sense for which kinds of goals, what counts as "at-risk
threshold" (default 20% behind pace).

## Action surface

- (L1 draft-only) — Q&A coaching to set up metrics; weekly status
  report
- (L4 structural-change) — write metrics + observations to
  `goal_tracking.db`

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{AGENCY_HOME}}/_state/goal_tracking.db"
      query: "SELECT * FROM goal_metrics"
      expect_min: 1
```

## Failure modes

- **Vanity metrics** — measuring something easy that doesn't actually
  prove progress (e.g. "emails sent" instead of "replies received").
  Self-check during setup: "if this number doubled, would
  {{OWNER_NAME}} say we'd made real progress toward the goal?"
- **Sourceless metrics** — defined the metric but never wired the
  data source. Skill flags after 14d of `no-data` status.
- **Goalpost-shifting** — operator silently moves target_value
  when behind pace. Audit log: every `define_metric` update is
  recorded; weekly status notes "target updated on <date>" if
  changed.
- **All-green theater** — every metric on-track. Sentinel-style
  check: if 100% of metrics on-track for 3 weeks running, surface
  "are you sure the bar is high enough?"

## Self-check

1. For each new metric: did I confirm the data source actually
   produces the number (not just describe it abstractly)?
2. For each "at-risk" verdict: did I include the specific gap
   ("X% achieved vs Y% expected at pace")?
3. For each "missed" verdict: did I surface this AS the lead item
   in the weekly report, not buried?
4. Did I run `sync_milestones_from_goals_md()` to keep the
   interim milestones in sync with the doc?
