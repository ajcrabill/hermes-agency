---
skill_id: morning-briefing
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, send-batched]
voice_tags: [warm-not-flattering, direct, we-not-i]
---

# Morning briefing

Daily summary delivered to {{OWNER_NAME}} at the configured time
(default 6am local). Covers calendar, email backlog, goals progress,
open delegations, and anything new since yesterday.

## What this skill does

Aggregate from across the system:

- **Calendar** — today's events from `calendar-manager`
- **Inbox** — items needing decision from `owner-channels-ingress`
- **Kanban** — tasks assigned to {{OWNER_NAME}}, plus stuck items
  CoS needs to surface
- **Goals progress** — daily checkpoint against `Goals.md::ACTIVE_PROJECTS`
- **Yesterday's outcomes** — what CoS sent, what specialists
  produced, what's now waiting on {{OWNER_NAME}}
- **Compliance** — quick flag if Sentinel raised any alerts overnight

Render as one focused email in the agency's voice. Sent batched.

## Inputs

- Current date + timezone
- `Personal.md`, `Goals.md` (context)
- Kanban + events.db + recent sent log

## Supervised learning

Rules tagged `morning-briefing`, `general`, `role:chief-of-staff`,
plus voice rules. Particularly: {{OWNER_NAME}}'s preferences for
length, format, what to include vs cut.

## Action surface

- (L1) draft the briefing → owner review
- (L2 send-batched) — send daily at scheduled time

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/briefings/{{DATE}}.md"
  - type: file_contains
    args:
      path: "/tmp/ha/briefings/{{DATE}}.md"
      needle: "## Today"
```

## Failure modes

- **Missing data source** — calendar API down, kanban empty. Render
  what's available; flag the missing sources.
- **Stale repeat** — yesterday's briefing content slipping into today's.
  Self-check against the prior day's content.
- **Tone drift** — briefing reads as bureaucratic. Voice rules catch it.

## Self-check

1. Is every section concrete (no placeholder filler)?
2. Is the calendar accurate for {{OWNER_NAME}}'s timezone?
3. Did I flag anything stuck waiting on {{OWNER_NAME}}?
4. Is the voice `we-not-I`?
5. Did I respect length preferences from learning rules?
