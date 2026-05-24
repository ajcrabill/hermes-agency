---
skill_id: quarterly-financial-summary
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct, undramatic]
---

# Quarterly financial summary

End-of-quarter package: P&L sketch, cash position trend, runway,
budget-vs-actual, revenue attribution, surprises. The quarterly
read-the-numbers session input.

## What this skill does

On the 15th of the month after quarter-end (gives bank
reconciliation time to land):

1. Cash position: opening / closing / delta
2. Revenue: total / by source / by client (top 5) / quarter-on-
   quarter trend
3. Expense: total / by category / trend
4. Burn rate + runway at quarter-end
5. Budget vs actual: the quarterly view from `budget-vs-actual`
6. Surprises: significant items (big new clients, big new
   expenses, write-offs, new vendor categories)
7. Looking forward: known commitments in the next quarter

Output: a markdown deliverable ready to share with collaborators
(after Analyst red-team, after KB IP-alignment review for any
client-mentioning content).

## Inputs

- `quarter` (e.g. "2026-Q3")
- Opening cash balance (operator-supplied)

## Supervised learning

Rules tagged `quarterly-financial-summary`, `general`,
`role:finance`. Operator preferences for length, level of detail,
collaborator audience.

## Untrusted content

If the summary is shared externally (collaborators, accountants),
KB + Analyst review it first — same review chain as any outbound.

## Action surface

- (L1 draft-only) — produce summary doc

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/finance/quarterly-{{QUARTER}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/_health/finance/quarterly-{{QUARTER}}.md"
      needle: "## Runway"
```

## Failure modes

- **Bank balance not reconciled** — opening/closing cash includes
  pending items. Self-check: confirm reconciliation completed
  before producing the summary; flag if not.
- **Cherry-picking** — including only good quarters in trend
  charts. Hard rule: every quarterly summary shows ≥4 quarters
  of trend.
- **Sharing too much** — including client-specific revenue in a
  summary shared externally. Hard rule: external-share version
  buckets by category, not by client name.

## Self-check

1. Did I name the reconciliation date for opening/closing cash?
2. Did I show ≥4 quarters of trend (not just this one)?
3. Did I flag surprises rather than smoothing them?
4. If for external share: did I bucket client-specific revenue?
5. Did KB + Analyst review external-share versions?
