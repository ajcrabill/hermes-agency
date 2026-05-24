---
skill_id: budget-vs-actual
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
---

# Budget vs actual

Periodic check against the operator's stated budget. For each
budget line: planned, actual, variance, variance %.

## What this skill does

Monthly (last day of month) and quarterly (last day of quarter):

1. For each `budget_lines` row matching the period, compute
   actual via `budget_vs_actual(period_start, period_end)`
2. Sort by absolute variance (biggest deltas surface first)
3. Render a report:
   - Lines >25% over plan
   - Lines >25% under plan
   - On-plan lines (within ±25%)
   - Lines with no actuals (planned but unused) — strong signal

Output goes to {{OWNER_NAME}} via CoS as a kanban task
(`tenant=finance`).

## Inputs

- `period_start`, `period_end`

## Supervised learning

Rules tagged `budget-vs-actual`, `general`, `role:finance`.
Operator threshold calibration (default 25% flag).

## Action surface

- (L1 draft-only) — produce report

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/finance/budget-vs-actual-{{PERIOD}}.md"
```

## Failure modes

- **Budget not set** — operator never created budget lines for the
  period. Skill emits `budget_vs_actual_skipped` event with
  recommendation to set lines for next period.
- **Category mismatch** — actual expenses categorized differently
  than budget lines. Variance gets attributed wrong. Mitigation:
  `expense-categorizer` enforces the same category vocabulary.

## Self-check

1. Did I sort by absolute variance, not by category name?
2. Did I include the "planned but unused" lines (often more
   actionable than over-budget)?
3. Is variance % computed correctly when planned is zero (return
   None, not infinity)?
