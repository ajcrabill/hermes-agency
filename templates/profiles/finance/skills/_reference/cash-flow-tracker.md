---
skill_id: cash-flow-tracker
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Cash flow tracker

Current cash position + near-term inflows + outflows + runway. The
answer to "where are we, financially, right now?" within 24h of
the most recent reconciliation.

## What this skill does

Daily (or on-demand):

1. Compute current position from `_framework.finance.cash_position(opening_cents=<bank-balance>)`
2. List upcoming inflows: unpaid `invoices_out` with `due_at` in the
   next 30 days
3. List upcoming outflows: unpaid `invoices_in` with `due_at` in the
   next 30 days + recurring expenses extrapolated from history
4. Compute runway via `runway_months()`
5. Produce a report: current / next-30 / next-90 view with explicit
   "assumes opening balance of X as of date Y"

Output is a kanban task body (`tenant=finance`) or `agency finance
cash-flow` CLI output.

## Inputs

- `opening_cents` — current bank balance (operator-supplied; the
  framework can't read banks directly)
- `as_of_date` — when that balance was true
- `window_days` (default 30)

## Supervised learning

Rules tagged `cash-flow-tracker`, `general`, `role:finance`.
Operator-calibration: which recurring expenses to extrapolate vs
treat as one-offs.

## Action surface

- (L1 draft-only) — produce report
- (L4 structural-change) — write reconciliation marker to
  `finance.db::meta` so future runs know the last opening balance

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/finance/cash-flow-{{TODAY}}.md"
```

## Failure modes

- **Stale opening balance** — operator hasn't updated bank balance
  in days; report uses old number. Self-check: flag staleness > 7d.
- **Missing invoices** — vendor invoice not yet logged. Reconciliation
  reveals; report flags "X% confident; bank statement reconciliation
  recommended."

## Self-check

1. Did I state the opening balance + its date explicitly?
2. Are upcoming inflows + outflows itemized (not aggregated)?
3. Did I include the runway computation?
4. Is the report dated + tied to a specific reconciliation point?
