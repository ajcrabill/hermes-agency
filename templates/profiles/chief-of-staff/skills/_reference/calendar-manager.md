---
skill_id: calendar-manager
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [direct, precise]
---

# Calendar manager

Read + write {{OWNER_NAME}}'s calendar. Detects conflicts. Enforces
the hard rules from `Personal.md::WORK_LIFE_BOUNDARIES` (e.g. "no
work after 7pm", "Saturdays for family"). Coordinates with Writing's
editorial calendar and BD's media pitch calendar.

## What this skill does

Three modes:

1. **Read** — return calendar events for a time range. Used by
   morning-briefing, conflict-detection, "do I have time for X."
2. **Propose** — given a request (meeting / call / focus block /
   content publication slot), find candidate times that don't
   conflict and respect hard rules. Return options.
3. **Write** — create / update / delete an event after explicit
   confirmation (L4 structural-change action class).

Hard rules from `Personal.md::WORK_LIFE_BOUNDARIES` apply at every
write — they can't be bypassed by autonomy level.

## Inputs

- Time range (read mode) or proposed event details (propose / write)
- Calendar credentials (`_framework/integrations/google_calendar.py`)
- `Personal.md` for hard-rule boundaries

## Supervised learning

Rules tagged `calendar-manager`, `general`, `role:chief-of-staff`.
Includes scheduling preferences ({{OWNER_NAME}}'s typical work hours,
preferred meeting durations, default buffer time between meetings).

## Action surface

- (L1) read + propose
- (L4) write events to the calendar

## Verifier criteria

```yaml
verifier:
  - type: http_status
    args:
      url: "https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={{TS}}"
      expect: 200
      # For read mode; write mode adds event-id existence checks
```

## Failure modes

- **Hard-rule violation** — proposed slot conflicts with
  `WORK_LIFE_BOUNDARIES`. Self-check catches; never reach write step.
- **Stale event** — event modified externally between propose + write.
  Re-read before write; abort if changed.
- **Time-zone confusion** — owner's timezone vs invitee's vs server.
  All times normalize to {{OWNER_NAME}}'s timezone from
  `deployment.yaml::deployment.timezone`.

## Self-check

1. Did I respect every hard rule from `WORK_LIFE_BOUNDARIES`?
2. For write mode: did I get explicit confirmation, or am I auto-
   writing at L5?
3. Is the timezone correct against `deployment.timezone`?
4. Did I check for conflicts against existing calendar entries?
