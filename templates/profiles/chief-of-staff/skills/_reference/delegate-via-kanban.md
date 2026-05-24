---
skill_id: delegate-via-kanban
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct]
---

# Delegate via kanban

Route work to specialist agents via the kanban with the right
`tenant`, `assignee`, and verifier criteria.

## What this skill does

Given an inbound work item, identify which specialist owns it +
create the kanban task with:

- `assignee` — the specialist's profile id
- `tenant` — the appropriate work category from
  `invariants.yaml::kanban_tenants`
- `skill` — the specific skill to use
- Verifier criteria for completion

Updates `Goals.md` and `operational-state.md` if the delegation is a
named project step.

## Inputs

- The work item (description + context)
- Sender (so the specialist has the relationship context)
- Priority + due-by

## Supervised learning

Rules tagged `delegate-via-kanban`, `general`, `role:chief-of-staff`.
Specifically: routing rules ("dossier requests go to Analyst",
"alignment checks go to KB"). Learning rules teach correct routing.

## Action surface

- (L1) create kanban task with full context

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT * FROM tasks WHERE id='{{NEW_TASK_ID}}' AND assignee IS NOT NULL AND tenant IS NOT NULL"
      expect_rows: 1
```

## Failure modes

- **Wrong specialist** — work assigned to the wrong role. Owner
  correction becomes a learning rule; recapture catches the repeat.
- **Missing context** — task body lacks sender info, prior thread,
  agency-vault context. Specialist has to ask back; bottleneck.

## Self-check

1. Is the specialist the right one for this work? Could KB do it
   instead of Analyst (or vice versa)?
2. Did I include enough context (sender, thread, agency-vault refs)
   that the specialist can act without round-tripping for clarification?
3. Did I set verifier criteria that mean something?
