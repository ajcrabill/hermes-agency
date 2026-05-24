---
skill_id: time-use-analyzer
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, precise]
---

# Time-use analyzer

Compares how {{OWNER_NAME}}'s time was actually spent (calendar +
kanban completions) against what `Goals.md` says we're optimizing
for. Surfaces the drift: where the stated priorities diverge from
where the hours actually went.

This is one of the most useful Chief of Staff functions. Stated
priorities are easy; lived priorities are what the calendar
actually shows. CoS makes that comparison visible weekly.

## What this skill does

For a given time window (default: last 7 days):

### 1. Pull the time-actually-spent data

- Calendar events via
  `_framework.integrations.google_calendar.list_events()`
- Kanban tasks completed within the window (claimed → done timestamps
  from `task_runs`)
- Optional: focus-block heartbeats if the operator has wired a
  pomodoro / focus tracker

### 2. Pull the stated priorities

- `Goals.md::ANNUAL_GOALS` (each goal's interim milestones)
- `Goals.md::Active strategic projects`
- `Personal.md::WORK_LIFE_BOUNDARIES` (hard rules — protected time)

### 3. Map each event to a goal (or `unmapped`)

For each calendar event + kanban completion:

- Match against goal text + project names by keyword
- Match against client names from `Clients.md`
- Match against author/coachee names from `multi-author-state` /
  per-subject state
- Anything that doesn't match: `unmapped` (free / admin / personal)

LLM does this mapping — pattern-match event summary/description
against the goals list.

### 4. Produce the drift report

For each goal + project:
- Hours allocated in the window
- % of work-hours in window (vs unmapped + other goals)
- Stated priority signal (if `Goals.md` has explicit weights, use
  those; else implicit order = priority)
- **Drift flag** if a high-priority goal got <10% of work-hours
  this week

Also:
- Hours in protected time (family / health) — was it actually
  protected, or eroded?
- Largest unmapped time blocks — what got done in them?
- Recommended re-allocations: "Tuesday 2-4pm was unbooked + Goal X
  is at 0% this week — block it for Goal X?"

### 5. Output

A markdown report rendered as a kanban task (`tenant=compliance`)
delivered Sunday morning as part of the weekly review, plus a
shorter daily flag in the morning briefing if a major drift is
detected.

## Inputs

- `window_days` (default 7)
- `profile_id` for the principal (looking up `Goals.md`,
  `Personal.md`, calendar credentials)

## Supervised learning

Rules tagged `time-use-analyzer`, `general`,
`role:chief-of-staff`. Per-operator calibration ("don't flag
research time as unmapped; that's allocated to Goal X" type
rules).

## Action surface

- (L1 draft-only) — produce drift report as kanban deliverable

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/time-use/{{WEEK_START}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/_health/time-use/{{WEEK_START}}.md"
      needle: "## Drift report"
```

## Failure modes

- **Calendar API down** — emit `time_use_skipped` event; produce
  partial report from kanban + heartbeats; flag the missing data
  in the report header.
- **Mis-categorization** — event mapped to wrong goal. Operator
  correction becomes a learning rule; recapture detector catches
  recurring miss.
- **Privacy leak** — personal events (medical, family) detailed in
  a report shared with the agency. Hard rule: `Personal.md`-
  related events are bucketed as "protected time" with NO detail
  surfaced.
- **Vanity reporting** — declaring a "win" because Goal A got 30
  hours when 25 of those were planning meetings. Self-check:
  separate execution vs planning vs admin time.

## Self-check

1. Did I pull events for the FULL window (no gaps from API errors)?
2. For each goal: did I cite the specific calendar events that mapped
   to it (so {{OWNER_NAME}} can verify the categorization)?
3. Did I flag drift only when it's actually material (≥10% gap +
   stated-priority signal)?
4. Did I respect `Personal.md` privacy — protected time named, not
   detailed?
5. Did I propose specific re-allocations (concrete time blocks),
   not vague "consider spending more time on X"?
