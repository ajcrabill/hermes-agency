---
skill_id: heartbeat-watch
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic]
---

# Heartbeat watch

Reads `heartbeats.db` for components that haven't beat in 2× their
expected interval. Files alerts for stale components. Runs every 5
minutes.

## What this skill does

Calls `_framework.sentinel.monitors.heartbeat_watch()`:

1. Reads `heartbeat_summary` for every tracked component
2. Compares `last_success_at` against
   `invariants.yaml::expected_intervals_seconds` for that component
3. Components past 2× their interval → emit `heartbeat_stale` event +
   file a kanban task `tenant=alert`
4. Components within interval → silent (no event spam)

Self-protection: Heartbeat-watch itself emits a heartbeat after each
run. If THIS skill stops, that's a meta-failure — operator notices
via Sentinel's own dashboard panel.

## Inputs

- `heartbeats.db`
- `invariants.yaml::expected_intervals_seconds`

## Supervised learning

Rules tagged `role:system-sentinel`.

## Action surface

- (read-only) — emit events + file kanban alerts

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{HEARTBEATS_DB}}"
  - type: sql_query
    args:
      db: "{{HEARTBEATS_DB}}"
      query: "SELECT * FROM heartbeats WHERE component='heartbeat-watch' ORDER BY ts DESC LIMIT 1"
      expect_rows: 1
```

## Failure modes

- **Component not tracked** — expected_intervals_seconds doesn't list
  it. Default to 300s (5m); add the component to invariants.yaml as a
  follow-up.
- **DB lock** — heartbeats are being written while we read. Retry
  once.

## Self-check

1. Did I emit my own heartbeat at end of run?
2. Did I dedup alerts (one per component per day)?
3. Is the alert body specific enough (component name, age, expected
   interval) that the operator can investigate?
