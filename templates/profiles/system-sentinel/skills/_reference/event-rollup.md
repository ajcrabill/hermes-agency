---
skill_id: event-rollup
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic]
---

# Event rollup

Hourly: rolls up the last hour's events into `events_hourly` for
fast trend queries. Without this, "how many recaptures in the last
30 days" requires scanning a large events table.

## What this skill does

Calls `_framework.sentinel.events_db.rollup_hour()`:

1. Aggregates the previous hour's events into
   `events_hourly` rows (one per kind × severity combo)
2. Replaces any existing row for that bucket (idempotent)
3. Emits an `event_rollup_ran` event with the bucket count

Cheap operation. Runs at minute 0 of every hour.

## Inputs

- `events.db`

## Supervised learning

Minimal rules. Sentinel's standards source covers this.

## Action surface

- (read-only outside events.db) — write to events_hourly + emit event

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{EVENTS_DB}}"
      query: "SELECT * FROM events_hourly ORDER BY bucket_ts DESC LIMIT 1"
      expect_rows: 1
```

## Failure modes

- **Empty hour** — no events to roll up. Skip silently; the empty
  bucket is correct.
- **Concurrent writes** — events still being appended for the same
  hour. Use `ON CONFLICT DO UPDATE` so partial bucket later corrects.

## Self-check

1. Did I emit my heartbeat?
2. Did the rollup transaction commit (or roll back cleanly)?
