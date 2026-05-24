---
skill_id: pipeline-watchdog
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, undramatic]
---

# Pipeline watchdog

Observability over CoS's own work pipeline. Surfaces things stuck.

## What this skill does

Every 15 minutes (or on-demand), scan:

- **Stale claims** — CoS-claimed kanban tasks unfinished after their
  expected duration
- **Stalled drafts** — drafts in queue without action for >24h
- **Missed cron** — heartbeats older than 2x expected interval for
  CoS-owned crons
- **Long-pending owner reviews** — items held >48h waiting on
  {{OWNER_NAME}}

For each, file a kanban task (`tenant=alert`) and emit an event.
Lighter than Sentinel's full audit — this watches CoS specifically.

## Inputs

- Kanban claim ages
- Heartbeats DB
- events.db

## Supervised learning

Rules tagged `pipeline-watchdog`, `general`. {{OWNER_NAME}}'s
patience thresholds (e.g. "anything over 4h stuck on me is a flag")
become rules here.

## Action surface

- (L1) file kanban alerts; never mutate state

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{EVENTS_DB}}"
      query: "SELECT * FROM events WHERE kind='pipeline_watchdog_ran' AND ts >= datetime('now', '-1 hour')"
      expect_min: 1
```

## Failure modes

- **Alert flood** — same stuck item repeatedly alerts. Idempotency:
  one alert per (item, status) pair per 24h.
- **False positive** — task legitimately takes longer than threshold.
  Owner marks the alert as not-actionable; rule captures.

## Self-check

1. Are alerts deduplicated against open ones?
2. Did I emit a heartbeat for myself?
3. If everything looks healthy, do I emit a silent-success event so
   {{OWNER_NAME}} can see the watchdog is still watching?
