---
skill_id: push-notify
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [laconic]
---

# Push notify

Desktop notifications for {{OWNER_NAME}} when CoS needs their
attention out-of-band (i.e. not via email or the morning briefing).
macOS / Linux / Windows native notifications via the appropriate
backend.

## What this skill does

Given a notification payload (title + body + optional kanban link):

1. Render the message at appropriate brevity (notifications get
   ~80 chars displayed; verbose content goes in the linked kanban)
2. Call the OS notification API (osascript on macOS, notify-send on
   Linux, win10toast on Windows)
3. Record the notification + dismissal/click outcome in events.db

Use sparingly — every push notification interrupts. The hard rule
is "important AND urgent" — anything that fails one of those goes
on the kanban or in the next morning briefing.

## Inputs

- `title` (≤80 chars)
- `body` (≤200 chars)
- `kanban_task_id` (optional — clicking notification opens this)
- `urgency` (low | normal | critical)

## Supervised learning

Rules tagged `push-notify`, `general`, `role:chief-of-staff`.
{{OWNER_NAME}}'s "what's worth interrupting me for" rules go here.

## Action surface

- (L1) — emit a notification + log to events.db

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{EVENTS_DB}}"
      query: "SELECT * FROM events WHERE kind='push_notify_sent' AND ts >= datetime('now', '-5 minutes')"
      expect_min: 1
```

## Failure modes

- **Notification flood** — every minor event becomes a push. Hard
  rule: rate-limit to N per hour; over N, batch and surface in
  the kanban instead.
- **OS backend missing** — `osascript` on a non-Mac, etc. Skill
  emits a `push_notify_skipped` event with the reason rather than
  failing.

## Self-check

1. Does this clear the "important AND urgent" bar?
2. Is the title ≤80 chars?
3. If it's not critical, should this go on the morning briefing
   instead?
4. Did I include a kanban link so {{OWNER_NAME}} can act on it
   from one click?
