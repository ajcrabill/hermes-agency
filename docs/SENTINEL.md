# System Sentinel — pure observability

Sentinel is HermesAgency's instrument panel. She watches every
system seam — learning, autonomy, kanban, verifier, send-guard —
and reports. She does not act.

## The role's hard constraints

Sentinel has read-only authority by code, not by convention:

- **Can:** read every profile's vault/db/state; watch logs; query
  databases; file kanban tasks (`tenant=alert / audit /
  compliance / recapture`); compute metrics; write to her own
  `events.db` table.
- **Cannot:** send mail; modify any other profile's files; alter
  configs; change skills; mutate the learning corpus; mutate
  autonomy state; restart services. *Anything that changes state
  outside her own table is forbidden.*

This is structural. An observer that can act becomes a participant
in what it's observing — and the observation gets compromised to
protect the action. Pinning Sentinel to read-only by code keeps
the watcher honest.

## Events database

`_state/events.db` — single append-only table. Every notable thing
in the agency lands here. Sentinel is the primary writer;
subsystems publish via `_framework.sentinel.append_event(...)`.

```python
from _framework.sentinel import append_event

append_event(
    kind="recapture_detected",
    actor="learning",
    target="rule-abc123",
    severity="critical",
    payload={"similar_to": "rule-xyz789", "similarity": 0.92},
)
```

The dashboard plugin tails this for the live feed. Trend queries
(`SELECT kind, COUNT(*) FROM events WHERE ts >= ?`) drive the
weekly health report.

## Cron monitors

Sentinel runs six recurring jobs. Each one emits events into her
own table and, when warranted, files a kanban task.

| Monitor | Cadence | Watches |
|---|---|---|
| `learning_monitor` | 5m | New `recapture_events` rows; emits a `recapture_detected` event per unacked one and files a kanban alert per skill implicated |
| `drift_monitor` | 15m | Per-skill drift score from the audit's most recent run; alerts on jumps above threshold |
| `heartbeat_watch` | 5m | `_state/heartbeats.db` — flags any component whose `last_success_at` is > 2× its expected interval |
| `playbook_audit` | Sun 04:00 | Full-fleet audit; appends per-rule findings to `events.db`; files a summary kanban task |
| `event_rollup` | hourly | Summarizes the last hour into `events_hourly` for fast trend queries |
| `compliance_report` | Sun 06:00 | Generates the weekly learning-loop health digest; files a kanban task |

Cadences are declared in `invariants.yaml::expected_intervals_seconds`.
`heartbeat_watch` uses them to compute "stale" — 2× the expected
interval.

## What Sentinel does NOT do

- Does not run the recapture *detector* — that runs at capture-time,
  inline, inside `capture_correction()`. Sentinel monitors recapture
  *events* and aggregates them.
- Does not gate promotions — that's `graduation_audit_gate.py`
  called from `record_event`. Sentinel records the events but
  doesn't author the decision.
- Does not author skills, fix bugs, or take ANY action beyond
  filing kanban tasks.

If Sentinel notices something wrong, her only output is a kanban
task with the structured event trace. The operator decides what to
do; another agent (or the operator) does it.

## Persona

Sentinel's persona is laconic, factual, undramatic. She doesn't try
to sound friendly. She reports what's true; the operator decides
what to do about it. Default `SOUL.md.template` ships with this
voice; deployments can edit but should resist making her chatty —
chatty observability is observability you trust less.

## Standards source

Unlike the other roles, Sentinel's `standards.md` is short. The
canonical descriptions of what good looks like live in:

- `framework-vault/MASTER_PLAN.md` — the deployment's stated
  architecture. Sentinel watches for drift from it.
- `framework-vault/DEVELOPMENT_PLAYBOOK.md` — the framework's
  quality standards. Sentinel runs audits against this doc.
- `_framework/invariants.yaml` — the framework constants the audit
  reads (ALWAYS_BLOCK list, role keywords, kanban tenants).

When the operator updates any of these, Sentinel's behavior tracks
the update automatically. There is no separate Sentinel doctrine
to maintain.

## CLI

```bash
agency events                       # recent events
agency events --kind recapture_detected
agency events --actor sentinel
agency events --tail --duration 300  # 5-minute live tail
```

The control panel (port 9118) also tails the events feed and
surfaces Sentinel-filed kanban alerts.
