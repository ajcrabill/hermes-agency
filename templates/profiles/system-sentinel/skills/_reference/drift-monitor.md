---
skill_id: drift-monitor
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic]
---

# Drift monitor

Computes per-skill drift score from the audit history (last 7 days
of findings vs. previous baseline). Alerts on significant jumps.
Runs every 15 minutes.

## What this skill does

Calls `_framework.sentinel.monitors.drift_monitor()`:

1. Reads `_health/audits/` history
2. For each skill, computes the count of new findings vs. baseline
3. Updates `_state/drift_scores.json` with the latest scores
4. If any skill's drift jump exceeds threshold, emits a
   `drift_alert` event + files a kanban task

For v0.3, baselines are simple (7-day rolling average); v0.4+ can
introduce statistical thresholds.

## Inputs

- Audit history JSON files in `_health/audits/`
- Threshold from `invariants.yaml` (or default)

## Supervised learning

Minimal rules tagged `role:system-sentinel`. Operator-adjusted
thresholds become rules.

## Action surface

- (read-only) — write drift_scores.json + emit events

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_state/drift_scores.json"
```

## Failure modes

- **No audit history yet** — skip silently, emit a `drift_monitor_skipped`
  event noting the reason.
- **Threshold mis-set** — fires too often or never. Operator
  retunes.

## Self-check

1. Did I emit a heartbeat?
2. Is the drift_scores.json valid JSON (not corrupted by partial write)?
3. Did I update the file atomically (write-then-rename)?
