---
skill_id: burn-rate-monitor
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, undramatic]
---

# Burn rate monitor

Rolling monthly burn (expenses + paid vendor invoices over the
trailing N months). Surfaces trend: are we trending up or down on
spending vs prior periods?

## What this skill does

Weekly (Sundays):

1. Compute trailing-3-month burn via `monthly_burn(months=3)`
2. Compare to trailing-12-month average
3. If current 3-month burn > 12-month avg by >15%, flag as
   "trending up" (with the specific categories that are growing)
4. If <85% of 12-month avg, flag as "trending down" (with category
   detail)

Output: short report (~5 lines) in the weekly review.

## Inputs

- None — pulls from `finance.db::expenses` + vendor_payments

## Supervised learning

Rules tagged `burn-rate-monitor`, `general`, `role:finance`.
Operator thresholds (default 15% flag-up, 15% flag-down) become
rules.

## Action surface

- (L1) — short report in the weekly review

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/finance/burn-{{WEEK_START}}.md"
```

## Failure modes

- **One-off skews trend** — a single large expense in the trailing
  3-month window distorts the average. Self-check: if any single
  expense is >25% of the period's total, call it out separately
  rather than baking it into the trend.
- **Category renames** — operator renamed a category mid-period.
  Trends become apples-to-pears. Self-check: warn when a category
  appears only in part of the window.

## Self-check

1. Did I name the specific months in the window?
2. If trending up: did I cite which categories grew + by how much?
3. Did I call out any outlier single expense rather than averaging
   it in?
