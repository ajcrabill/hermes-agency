---
skill_id: red-team
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, precise]
---

# Red team

Adversarial review of a draft, plan, or proposal. Returns one of
three verdicts: `approve` / `revise: <specifics>` / `block:
<specifics>`. Always names specific failure modes when not
approving.

## What this skill does

Receive an artifact + a kanban task id. Read it carefully. Steelman
the case against. Hunt for the load-bearing assumption. Check cited
sources. Surface the specific failure modes. Post the verdict back
to the kanban task as a comment.

This is the discipline of caring about being wrong as much as being
right. Adversarial without performative cynicism.

## Inputs

- `artifact_path` or `artifact_text` — what to review
- `kanban_task_id` — where to post the verdict
- `review_depth` — one of `quick-take` (first impression, no
  adversarial pass) or `full-adversarial` (default)

## Supervised learning

Loads applicable rules at skill-load. Particularly relevant:

- `general` rules about reasoning discipline
- `role:analyst-judge` rules about verdict thresholds
- `red-team` rules about specific failure-mode patterns to watch
  for

**Recording firings:**

```python
from _framework.learning import record_firing
record_firing(rule_id="<id>", skill_tag="red-team",
              profile="{{ANALYST_ID}}",
              action_summary="flagged unsupported claim per rule X")
```

## Action surface

- (L1 draft-only) — posts a verdict comment on the kanban task.
- (L4 structural-change) — when a recurring pattern emerges,
  proposes a new learning rule to the curation queue (`learning-
  curation` skill picks it up).

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT body FROM task_comments WHERE task_id='{{TASK_ID}}' AND author='{{ANALYST_ID}}'"
      expect_min: 1
  - type: file_contains
    args:
      path: "/tmp/ha/verdicts/{{TASK_ID}}.md"
      needle: "verdict:"   # the verdict must be explicitly named
```

## Failure modes

- **Vague verdict** — "feels iffy" instead of a named failure mode.
  Self-check rejects.
- **Approval-without-reading** — the verdict comes back too fast,
  with no specific reasoning. The verifier checks the verdict text
  for cited evidence.
- **Performative skepticism** — listing concerns without checking
  if they actually apply. The principal pushes back; the firing
  records `was_overridden=True`.
- **Bottlenecking** — review sitting in queue too long. Self-track
  the time-to-verdict; alert if > 24h.

## Self-check

Before the verdict ships:

1. Is the verdict one of the three (`approve` / `revise` / `block`)?
2. If approving: 1-3 sentences naming the specific strengths.
3. If revising: each requested change specific enough that the
   producer doesn't have to guess what to change.
4. If blocking: the failure mode is named, not just gestured at.
5. Did I steelman the opposite case before deciding?
6. Did I check the cited sources, or did I take them on faith?
