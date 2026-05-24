---
skill_id: strategic-plan-health-check
profile: __shared__
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
interim_goal: __cross__
outcome: __cross__
outcome_metric: strategic-plan health drift surfaced within 7 days of occurrence
status: green
alignment_argument: |
  This skill IS the weekly cadence that StrategicPlanning.md §7.4 requires.
  It's the input layer of the three-layer testability model — without it
  the strategic plan ossifies. Cross-cuts every Outcome / Interim Goal /
  Initiative; cadence: weekly.
---

# Strategic-plan health check (weekly)

The CoS's weekly check on whether the strategic plan is actually
moving the needle. Reads Goals.md (three-layer) + goal-tracking DB
+ firings DB + audit findings, and produces a short plain-language
summary that names the one or two things that have drifted and
proposes a pivot.

The strategic plan is a tool for **pivoting**, not a tool for
self-congratulation. The point of this check isn't to celebrate
green; it's to find what isn't working and propose what to do
about it.

## What this skill does

Per StrategicPlanning.md §7.4:

1. **For each Outcome:** is the lagging indicator moving in the
   right direction at the expected pace? (Often the data isn't
   there yet — note that as a signal.)

2. **For each Interim Goal:** is the SMART metric on track? If
   not, what does the data say about why?

3. **For each Initiative (skill / script):** are the firings
   happening on cadence? Are artifacts being produced?

4. **Audit:** how many strategic-alignment findings are open?

5. **Pivot proposals:** select the 2-3 most pressing drift signals
   and frame each as a concrete pivot the Principal could consider.

## When this skill fires

Cadence: **weekly** (default: Monday morning). Either:

  - The CoS profile's weekly cron triggers a `strategic-plan-health-check`
    cron job that calls `run_health_check()` + posts the rendered
    report to the Principal's inbox / kanban / Slack.
  - The Principal invokes manually: *"give me the weekly health check"*

## Inputs

- None directly. Reads:
  - `Goals.md` (three-layer)
  - `~/.hermes/agency-state/_state/goal_tracking.db`
  - `~/.hermes/agency-state/_state/learning.db` (firings)
  - audit findings (via `audit_deployment()`)

## Outputs

- A plain-language markdown report (~< 60 seconds to read).
- The pivot proposals are surfaced *first*; the layer-by-layer detail
  comes after.
- Format mirrors §7.4's intent: short, name the drift, propose the pivot.

## How to invoke from Python

```python
from _framework.strategic_health import run_health_check, render_report

report = run_health_check()
print(render_report(report))
```

## Supervised learning

Rules tagged `strategic-plan-health-check`, `chief-of-staff`. Per-Principal
calibration for how aggressive the pivot proposals should be (some
Principals want every signal flagged; others only want clear drift).

## Action surface

- (L1 draft-only) — reads vault docs + DBs, produces a markdown report.
  Never mutates Goals.md / Guardrails.md / any skill file.

## Verifier criteria

```yaml
verifier:
  - type: report_structure
    args:
      sections_required:
        - "Pivots worth considering this week"
        - "Outcomes"
      reads_only: true
```

## Failure modes

- **No three-layer Goals.md** — deployment hasn't been set up with
  the strategic-planning structure. Output names this clearly + points
  at `/agency setup`.
- **No metrics defined** — Outcomes + Interim Goals exist in Goals.md
  but no metrics in `goal_tracking.db`. Report shows the structure
  but every IG is "no-data". This is the expected state right after
  setup; the Principal should run `define_metric()` for each IG.
- **Pivot fatigue** — every week proposes the same pivots. The
  supervised-learning loop should pick this up + tag a recapture
  event so the Principal can deliberately decide *not* to pivot.

## Self-check

1. Did the report start with the pivot proposals (not the celebration)?
2. Were the pivot proposals concrete (named the IG, named the
   Initiative, suggested *what* to change)?
3. Did the report stay under ~60 seconds to read?
4. Did I avoid framework jargon ("SMART," "Interim Goal," "Initiative
   ref") in the pivot proposals themselves, or use plain language?
