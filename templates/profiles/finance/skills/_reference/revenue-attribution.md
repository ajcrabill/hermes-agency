---
skill_id: revenue-attribution
profile: {{FINANCE_ID}}
role: finance
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Revenue attribution

When revenue lands, trace it back to the originating outreach /
referral / event. BD + {{OWNER_NAME}} use this to see what
marketing is actually working.

## What this skill does

Triggered when a `revenue` row is added:

1. Check whether the client has BD CRM history (sent_threads,
   journalists tracked, podcast pitches). If yes, the lead's
   source becomes the attribution.
2. If no BD history, check `Clients.md` for the source field
   (referral, inbound, renewal of prior engagement).
3. Default: `unattributed` — surfaces as a question in the
   monthly summary ("we don't know where this came from").

Weekly: produce a top-of-funnel report via
`revenue_attribution_summary()` — % of revenue per source.

## Inputs

- `revenue_id` — the row just added
- BD CRM data + Clients.md for cross-reference

## Supervised learning

Rules tagged `revenue-attribution`, `general`, `role:finance`.
Per-source classification rules ("if the client first appeared in
sent_threads via a journalist pitch, attribute to journalist-pitch
not bd-outreach").

## Action surface

- (L1 draft-only) — propose attribution
- (L4 structural-change) — write to `revenue.source` field

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{FINANCE_DB}}"
      query: "SELECT source FROM revenue WHERE id={{REVENUE_ID}} AND source != 'unattributed'"
      expect_rows: 1
```

## Failure modes

- **Multi-touch attribution** — client found us via podcast +
  later signed via direct outreach. Hard problem; document the
  ambiguity rather than picking arbitrarily. Default to first-
  touch unless operator says otherwise.
- **Stale CRM data** — BD CRM doesn't have the client recorded
  but they came through BD. Surfaces as `unattributed`;
  monthly summary asks operator.

## Self-check

1. Did I check BD CRM first?
2. If multiple plausible sources: did I document the ambiguity?
3. If `unattributed`: did I add to monthly-question list?
