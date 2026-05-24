---
skill_id: verifier-criteria-author
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Verifier criteria author

Authors typed verifier criteria for new task types. When a skill
introduces a task shape the existing criterion types don't cover,
this skill proposes new criteria (or, if needed, a new criterion
type).

## What this skill does

Given a task description + expected output:

1. Inventory existing criterion types
   (`agency verifier list-types`)
2. Identify which existing types fit
3. If none fit, propose a new type with the handler signature +
   purpose
4. Write the proposed criteria YAML
5. Submit as a PR-ready proposal (kanban task)

Skills that lack good criteria are skills the verifier can't
trust — fail-closed means no completion. This skill exists so the
framework grows new verifier types deliberately, not by hand-wave.

## Inputs

- Task description + expected output shape
- The skill that owns the task

## Supervised learning

Rules tagged `verifier-criteria-author`, `general`,
`role:analyst-judge`.

## Action surface

- (L1) — proposal as kanban comment

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/verifier-proposals/{{PROPOSAL_ID}}.yaml"
```

## Failure modes

- **Over-typed proposal** — new criterion type proposed when an
  existing one fits with different args. Self-check: did I really
  exhaust the existing types?
- **Untyped fallback** — proposes `shell_exit_zero` as a default
  rather than a real typed criterion. Hard rule: shell_exit_zero is
  a last resort, not a default.

## Self-check

1. Did I enumerate the existing types before proposing new?
2. If proposing new: is it ONE new type, with a clear purpose?
3. Are my proposed criteria yaml-valid?
4. Did I avoid `shell_exit_zero` unless absolutely necessary?
