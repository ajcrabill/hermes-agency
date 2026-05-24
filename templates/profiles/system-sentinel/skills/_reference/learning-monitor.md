---
skill_id: learning-monitor
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic, undramatic]
---

# Learning monitor

Watches `recapture_events`. When the learning loop detects a duplicate
correction, this skill surfaces it to the operator. Runs every 5 min.

## What this skill does

Calls `_framework.sentinel.monitors.learning_monitor()`:

1. Queries `recapture_events` for rows where `notified=0` and
   `dismissed=0`
2. For each: emits a `recapture_detected` event into `events.db`
3. Files a kanban task tagged `tenant=recapture` with the full
   context (new rule + matched prior rule + similarity + skill_tags)
4. Marks the recapture event as `notified=1`

The skill itself runs no judgment — it surfaces what the recapture
detector already concluded. The operator decides what to do.

## Inputs

- The learning DB (read-only)
- The kanban (write-only, alerts)

## Supervised learning

Sentinel's standards live in framework-vault docs (master plan +
playbook). The skill loads minimal rules tagged
`role:system-sentinel`.

## Action surface

- (read-only) — write events; file kanban alerts

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{EVENTS_DB}}"
      query: "SELECT * FROM events WHERE kind='recapture_detected' AND ts >= datetime('now', '-1 hour')"
      expect_min: 0   # may be zero if nothing happened; verifier passes
```

## Failure modes

- **Alert flood** — same recapture event fires repeatedly. Mitigated
  by the `notified=1` flag once we file the alert.
- **DB lock** — recapture_events being written while we read. Retry
  once with backoff.

## Self-check

1. Did I emit a heartbeat for myself after the run?
2. Did I check `dismissed=0` so denylisted recaptures don't re-alert?
3. Is the kanban task body specific enough that the operator can
   investigate without re-querying?
