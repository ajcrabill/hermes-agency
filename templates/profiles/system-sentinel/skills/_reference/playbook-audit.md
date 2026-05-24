---
skill_id: playbook-audit
profile: {{SENTINEL_ID}}
role: system-sentinel
autonomy:
  min_level: 1
  action_classes: []
voice_tags: [laconic, undramatic]
---

# Playbook audit

Sunday 04:00 — runs the full audit against every profile + the
framework itself. Writes findings to `_health/audits/`, emits an
`playbook_audit_ran` event, files a summary kanban task.

## What this skill does

Calls `_framework.sentinel.monitors.playbook_audit()` which delegates
to `_framework.audit.audit_alignment.audit_deployment()`:

1. Audits every profile (all categories, including warns)
2. Audits the framework against itself (`audit_self()`)
3. Writes the full report JSON to
   `_health/audits/{{YYYY-MM-DD}}.json`
4. Diffs against last week's findings (which improved, which
   regressed, what's new)
5. Files a kanban task `tenant=audit` with the summary

Operator reads the Sunday-morning audit summary as part of the
weekly review.

## Inputs

- Every profile + the framework
- Last week's audit (for diff)

## Supervised learning

Rules tagged `role:system-sentinel`. Particularly: thresholds for
"call this out in the summary" vs "include in the appendix."

## Action surface

- (read-only) — write audit report, emit event, file kanban

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/audits/{{TODAY}}.json"
  - type: sql_query
    args:
      db: "{{EVENTS_DB}}"
      query: "SELECT * FROM events WHERE kind='playbook_audit_ran' AND ts >= datetime('now', '-2 hour')"
      expect_min: 1
```

## Failure modes

- **Audit module import fail** — `_framework.audit` not available.
  Emit `playbook_audit_skipped` event with reason.
- **Long-running** — audit takes too long on large deployment.
  Time-cap each rule; emit partial result.

## Self-check

1. Did I emit my heartbeat?
2. Did I write the full JSON before emitting the event (atomic)?
3. Did I include the regression diff in the summary?
