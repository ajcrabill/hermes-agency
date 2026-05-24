---
skill_id: weekly-opportunity-scan
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, undramatic]
---

# Weekly opportunity scan

Sunday strategic pipeline summary. What's progressing, what's
stalled, what to do next week. Pipeline truth, not pipeline hope.

## What this skill does

For each lead in the CRM:

- Current stage + days-in-stage
- Last touch + days since
- Sentiment of last reply
- Recommended next action (follow-up / pivot / archive)

For each open media opportunity:

- Where it is in the booking arc
- Next milestone
- What I need from CoS or {{OWNER_NAME}}

Conversion summary (this week vs last week vs trend).

Output is a kanban task `tenant=bizdev` posted Sunday morning.

## Inputs

- CRM tables (leads / sent_threads / reply_log / contacts)
- Media-opportunity tracking

## Supervised learning

Rules tagged `weekly-opportunity-scan`, `general`,
`role:business-development`.

## Action surface

- (L1) — produce summary as kanban task

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT * FROM tasks WHERE assignee='{{OWNER_HANDLE}}' AND tenant='bizdev' AND created_at >= datetime('now', '-2 days')"
      expect_min: 1
```

## Failure modes

- **Pipeline hope** — inflate stages to look better. Hard rule:
  match status to last reply sentiment.
- **Buried lede** — bury a stalled critical lead. Top of summary is
  always "what's actually moving + what's at risk."

## Self-check

1. Is every status backed by the actual reply log?
2. Did I name what's stalled, not just what's moving?
3. Did I propose a specific next action per item?
4. Did I include the week-vs-week conversion trend?
