---
skill_id: obligation-board
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Obligation board

{{OWNER_NAME}}'s commitments — what they said they'd do, by when,
to whom — tracked as a first-class surface. Different from kanban
(work to be done by the agency) — this tracks {{OWNER_NAME}}'s
own commitments, which CoS shepherds.

## What this skill does

Every inbound message that contains an explicit {{OWNER_NAME}}
commitment ("I'll send the slides by Friday", "let me think about
this and get back to you", "I'll introduce you to X") gets parsed
into an obligation:

  obligation_id, to_whom, what, due_by, source_message_id,
  status (open | in_progress | done | renegotiated | dropped),
  last_nudge_at, days_overdue

Daily, CoS scans obligations + surfaces:

- Due today / due tomorrow → top of morning briefing
- Overdue 1-3 days → "needs your attention"
- Overdue 4-7 days → "needs to be renegotiated or dropped"
- Overdue >7 days → counts against the agency's "said-vs-done"
  metric in weekly review

Obligations are stored in a small per-CoS DB:
`profiles/<cos>/state/obligations.db`.

## Inputs

- Inbound message text + sender (extract commitments)
- Outbound draft text (extract commitments BEFORE send so we
  capture the moment of making the promise)

## Supervised learning

Rules tagged `obligation-board`, `general`,
`role:chief-of-staff`. Includes calibration ("anything starting
with 'I will' or 'let me' is a candidate commitment").

## Action surface

- (L1) — propose obligation extractions, ask {{OWNER_NAME}} to
  confirm
- (L4 structural-change) — write to obligations.db

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{COS_ID}}/state/obligations.db"
```

## Failure modes

- **False-positive extraction** — flagging "I think it'd be great
  to..." as a commitment. Hard rule: only extract explicit
  commitments with a what + (ideally) a when.
- **Lost commitment** — {{OWNER_NAME}} commits something verbally
  / via Signal that CoS doesn't see. Mitigation: {{OWNER_NAME}}
  can `agency state append --section "Open commitments" ...` to
  add one manually.
- **Renegotiation friction** — overdue obligations are uncomfortable.
  CoS surfaces them anyway — that's the value.

## Self-check

1. For each extracted commitment: who, what, by when? If I can't
   answer all three, don't extract.
2. When surfacing overdue ones: did I include the specific text
   {{OWNER_NAME}} committed?
3. Is the cadence right (don't surface the same obligation 7 days
   in a row — escalate the friction over time)?
