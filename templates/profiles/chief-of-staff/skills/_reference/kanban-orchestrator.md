---
skill_id: kanban-orchestrator
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [direct]
---

# Kanban orchestrator

Claims CoS's own kanban tasks, spawns delegation tasks for specialists,
and collects results back into the right downstream skill.

## What this skill does

Every 5 minutes (or on-demand), poll the kanban for tasks assigned
to CoS, ready, with no unresolved `blocks` parents. For each:

- Decide whether CoS handles it or delegates
- If delegating: create a child task with the right `assignee` +
  `tenant` + `blocks` link
- If handling: spawn the appropriate sub-skill task (draft-composer,
  send-orchestrator, etc.)
- Watch for results posted back as comments; complete with verifier
  when the verifier criteria pass

Uses `_framework.kanban.claim_task_for_skill()` for atomic claim,
`_framework.kanban.complete_with_verifier()` for completion.

## Inputs

- The kanban DB (current board)
- Per-task `tenant` + `assignee` + `skill` metadata

## Supervised learning

Rules tagged `kanban-orchestrator`, `general`, `role:chief-of-staff`
inject. Particularly important: rules about WHEN to delegate vs.
handle inline.

## Action surface

- (L1 draft-only) — claim tasks, create child tasks, post comments
- (L4 structural-change) — close tasks via verifier, update status

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT * FROM tasks WHERE id='{{TASK_ID}}' AND status IN ('done', 'claimed', 'blocked')"
      expect_rows: 1
```

## Failure modes

- **Umbrella deadlock** — parent task waiting on children that wait
  on parent. Mitigated by the `tracks`/`blocks` distinction
  (use `tracks` for aggregating umbrella tasks).
- **Wrong delegation** — task routed to wrong specialist. Owner
  correction becomes a learning rule.
- **Lost result** — specialist posted result but orchestrator didn't
  pick up. Verifier re-checks; if results are present but task is
  still claimed, recover the result.

## Self-check

1. Did I check `blocking_parents()` before claiming?
2. If delegating: is the child task's `assignee` + `tenant` right?
3. Did I use `tracks` (not `blocks`) for aggregate umbrellas?
4. Did `complete_with_verifier` actually run? (Not skipped.)
