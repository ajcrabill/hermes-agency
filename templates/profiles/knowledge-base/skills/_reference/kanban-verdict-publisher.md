---
skill_id: kanban-verdict-publisher
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Kanban verdict publisher

The standardized way KB posts verdicts back to the kanban. Used by
`ip-alignment-check`, `methodology-application-check`,
`quality-auditor`, `meeting-evaluator`.

## What this skill does

Format a verdict into a structured kanban comment:

- Verdict line (e.g. `aligned`, `divergent: <reasons>`,
  `gap: <missing>`, `correctly-applied`, etc.)
- Cited sources (corpus document refs)
- Specific changes requested (for divergent / gap)
- Score (for quality-auditor)

Post the comment to the artifact's kanban task. Update task status
appropriately (`ready` → `verified` on `aligned`; `ready` →
`blocked` on `divergent` requiring producer rework).

## Inputs

- `task_id` — kanban task
- `verdict` — structured verdict object from one of KB's evaluator
  skills
- `produced_by` — which specialist made the artifact

## Supervised learning

Rules tagged `kanban-verdict-publisher`, `general`. Particularly:
format conventions (how to phrase a `gap` so the producer knows what
to do).

## Action surface

- (L1) post comment, update task status

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT * FROM task_comments WHERE task_id='{{TASK_ID}}' AND author='{{KB_ID}}'"
      expect_min: 1
```

## Failure modes

- **Verdict ambiguity** — comment doesn't clearly name a specific
  verdict. Verifier checks for verdict-keyword presence.
- **Wrong status transition** — task moved to `done` when it should
  stay `blocked`. Status transitions are constrained by the
  verdict type.

## Self-check

1. Is the verdict word explicit (`aligned` / `divergent: X` /
   etc.), not vague?
2. Did I cite sources for any claims I made?
3. For divergent: did I name what specifically to change?
4. Did I set the right task status?
