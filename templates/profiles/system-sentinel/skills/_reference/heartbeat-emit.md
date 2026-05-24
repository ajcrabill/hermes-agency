---
skill_id: heartbeat-emit
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic, undramatic]
---

# Heartbeat emitter (self-check)

Emits a heartbeat for `system-sentinel` itself. Runs every 5 minutes
via cron. If Sentinel stops emitting, `heartbeat_watch` (which
Sentinel also runs) won't notice — so the framework's external cron
infrastructure is the canary on Sentinel itself.

This is the simplest skill in the framework. It exists to:
1. Confirm Sentinel's cron job is firing
2. Test the heartbeat path end-to-end every 5m

## What this skill does

```python
from _framework.heartbeats import beat
beat("system-sentinel")
```

That's it. Records a row in `heartbeats.db` + bumps the
`heartbeat_summary` row for `system-sentinel`.

## Inputs

None.

## Supervised learning

Loads applicable rules at skill-load (none expected for v0.1, but
the framework wires this for consistency).

```python
from _framework.learning import inject_for_skill
text = inject_for_skill(skill_name="heartbeat-emit",
                        profile="{{SENTINEL_ID}}",
                        role="system-sentinel")
```

Records firings if any rule shaped the heartbeat (rare for this
skill — heartbeat semantics are deterministic).

## Action surface

- (L1 only) — write to Sentinel's own table (heartbeat). Sentinel
  declares NO action classes other than this minimal self-tracking.

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{HEARTBEATS_DB}}"
      query: "SELECT * FROM heartbeats WHERE component='system-sentinel' ORDER BY ts DESC LIMIT 1"
      expect_rows: 1
```

## Failure modes

- **DB locked** — heartbeats.db is being written by another process.
  Retry once with 100ms backoff; if still locked, log and move on
  (cron will fire again in 5m).
- **Schema mismatch** — heartbeats.db schema_version > what this
  build supports. Hard fail with clear message; operator upgrades
  the framework.

## Self-check

1. Did the heartbeat row land?
2. Is `heartbeat_summary` for `system-sentinel` updated?
