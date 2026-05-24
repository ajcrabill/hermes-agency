---
skill_id: send-orchestrator
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, send-batched, send-single]
voice_tags: [we-not-i]
---

# Send orchestrator

The canonical outbound mail path. Every send routes through this
skill: it runs the send-guard, applies hard ceilings, checks access
lists, and either sends or holds.

## What this skill does

Receive a draft (from `draft-composer`, a specialist via kanban,
or directly from {{OWNER_NAME}}). Validate it through
`_framework.send_guard.evaluate()`. Per the verdict:

- **ALLOW** → send (via Himalaya CLI or configured SMTP transport),
  log the sent thread, post a kanban comment with the message id
- **HOLD** → queue for owner review on the kanban with the reason
- **DENY** → refuse + record the firing(s) with `was_overridden=1`,
  file a kanban alert tagged `tenant=alert`

This is the ONLY send path in the default deployment. Specialist
agents draft; this skill sends.

## Inputs

- `draft` — to/cc/bcc/subject/body + intended_action_class
- `kanban_task_id` (optional) — to post results back

## Supervised learning

Rules tagged `send-orchestrator`, `general`, `role:chief-of-staff`
inject. The send-guard's hard-rule validators (loaded from
`learning_rules WHERE is_hard=1`) compose with the autonomy-gate
action-class check.

## Action surface

- (L2 send-batched) — adds to next batch
- (L3 send-single) — sends immediately on ALLOW
- Hard ceilings always apply regardless of level (first-message-to-
  new-contact, blacklist, never-autonomous-send-per-recipient)

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{LEARNING_DB}}"
      query: "SELECT * FROM firings WHERE skill_tag='send-orchestrator' AND created_at >= datetime('now', '-1 hour')"
      expect_min: 1
  - type: file_exists
    args:
      path: "/tmp/ha/sent-log/{{MESSAGE_ID}}.json"
```

## Failure modes

- **Send-guard bypass** — outbound goes out without `evaluate()`
  being called. Hard rule violation; audit catches.
- **Hard-rule override missed** — validator fails to catch a
  violation. Recapture detection catches the recurring pattern.
- **Transport failure** — SMTP/IMAP error. Retry once with backoff;
  if still failing, file alert and hold.

## Self-check

1. Did the send-guard verdict actually fire? (Not skipped.)
2. If DENY: did I record the firings with `was_overridden=1`?
3. If HOLD: is the kanban task created with the right context for
   owner review?
4. If ALLOW: is the sent-thread logged for the CRM + reply matcher?
