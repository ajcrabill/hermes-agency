---
skill_id: obligation-extractor
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Obligation extractor

Parses explicit commitments {{OWNER_NAME}} makes (in messages they
send, or that arrive expecting a response) and creates kanban tasks
that track them. The kanban *is* the tracking surface; this skill is
the *sourcing* layer.

## What this skill does

For every consequential message touching {{OWNER_NAME}} (inbound or
outbound), scan for explicit commitments:

- **Outbound, by {{OWNER_NAME}}:** "I'll send the slides Friday",
  "let me think about this and get back to you", "happy to make the
  intro to X"
- **Outbound, by CoS on behalf of {{OWNER_NAME}}:** same shapes, but
  CoS knows it was authorized
- **Inbound expecting commitment:** "can you confirm by Wednesday?",
  "let me know" — extract the *implied* commitment {{OWNER_NAME}}
  hasn't made yet, surface to {{OWNER_NAME}}

For each extracted commitment, create a kanban task:

```
assignee:  <principal>
tenant:    obligation
title:     "→ <to_whom>: <what>"
due_by:    <when, if stated>
body:      <quoted commitment text + source message link>
```

If the message also implies an obligation FROM the recipient back to
us, create a parallel task with `assignee=cos` + `tenant=cross-profile-msg`
so CoS shepherds the follow-up.

## Inputs

- `message_id` + direction (inbound | outbound)
- Sender / recipient identifiers
- Message text

## Supervised learning

Rules tagged `obligation-extractor`, `general`, `role:chief-of-staff`.
{{OWNER_NAME}}'s commitment-language patterns ("anything starting
with 'I will' or 'let me' is a candidate") become rules. Calibration
over time: too-aggressive extraction creates kanban noise; too-
conservative misses real commitments.

## Action surface

- (L1) — propose extractions for {{OWNER_NAME}} to confirm
- (L4 structural-change) — create kanban tasks directly (after
  earning track record)

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT * FROM tasks WHERE tenant='obligation' AND created_at >= datetime('now', '-1 hour')"
      expect_min: 0   # may be zero this hour; passes either way
```

## Failure modes

- **False positive** — flagging "I think it'd be great to..." as a
  commitment. Hard rule: extract only when there's a what + (ideally)
  a when AND an explicit verb ("will" / "let me" / "happy to").
- **Lost commitment** — {{OWNER_NAME}} committed something verbally
  (Signal, in person) that this skill never saw. Mitigation:
  `agency state append --section "Open commitments" --body "..."`
  to log manually. Also surfaces in morning-briefing as "anything
  I committed to that you missed?"
- **Wrong-direction extraction** — treating an inbound ask AS the
  principal's commitment. Direction tag prevents this.

## Self-check

1. Is there a clear what + (ideally) when + to whom? If not, don't
   extract.
2. Did I quote the exact committing text in the kanban task body?
3. Did I link the source message?
4. For implied-commitments (inbound expecting response), did I surface
   the *implicit* commitment to {{OWNER_NAME}} rather than auto-
   commit?
