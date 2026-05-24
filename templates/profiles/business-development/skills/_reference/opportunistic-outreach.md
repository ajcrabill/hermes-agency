---
skill_id: opportunistic-outreach
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only, send-batched]
voice_tags: [direct]
---

# Opportunistic outreach

Same-day outbound draft generation based on news/events. When a
prospect, journalist, or podcast host does something that warrants
contact today (not next week), this skill drafts the outreach in
hours.

## What this skill does

Triggered by either:

- A signal from `prospect-research` (news event landed)
- A signal from `journalist-relationship` (covered an adjacent topic)
- A direct kanban task from CoS

For each signal:

1. Confirm the prospect/journalist isn't already on a stalled
   sequence
2. Draft the outreach in the agency's voice (lead with the
   triggering event — that's the "why now")
3. Run draft past KB for IP alignment (if framework claims are made)
4. Hand to CoS via kanban for review + send

Optimize for speed: a same-day draft is worth more than a perfect
late one.

## Inputs

- `signal_id` — what fired
- `target_id` — the prospect/journalist/host
- `triggering_event` — the news/article URL + date

## Supervised learning

Rules tagged `opportunistic-outreach`, `general`,
`role:business-development`. Includes calibration on "value-first
contact" + which signal types warrant outreach.

## Untrusted content

External signal sources pass through prompt-injection scanner.

## Action surface

- (L1) — draft → CoS
- (L2 send-batched) — adds to outreach batch (CoS approves)

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/outreach-drafts/{{SIGNAL_ID}}.md"
  - type: file_contains
    args:
      path: "/tmp/ha/outreach-drafts/{{SIGNAL_ID}}.md"
      needle: "why now:"
```

## Failure modes

- **Stale signal** — news event is more than 48h old, no longer
  "why now." Self-check filters.
- **Duplicate outreach** — same prospect targeted by two signals.
  CRM check before drafting.
- **Off-topic** — signal matches keywords but isn't actually
  relevant. KB-alignment-check catches.

## Self-check

1. Is the "why now" within 48 hours of the triggering event?
2. Did I check the CRM for prior contacts?
3. Is the value-first principle honored (offering, not asking)?
4. Does the draft cite the specific triggering event?
