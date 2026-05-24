---
skill_id: ip-alignment-check
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# IP alignment check

Validates a draft artifact (email, post, proposal, workbook page)
against {{ORG_NAME}}'s IP corpus. Returns one of three verdicts:
`aligned` / `divergent: <reasons>` / `gap: <what's missing>`.

## What this skill does

Receive an artifact + a kanban task id. Load the relevant IP
corpus documents from `context/{{KB_ID}}/ip/`. Compare. Produce a
verdict comment back on the kanban task.

No drafting. No production. Verdicts and annotations only.

## Inputs

- `artifact_path` or `artifact_text` — what to evaluate
- `kanban_task_id` — where to post the verdict
- `domain_hint` (optional) — which area of the IP corpus to focus on

## Supervised learning

Loads applicable rules at skill-load. Particularly important:

- `general` rules about citation discipline
- `role:knowledge-base` rules about verdict thresholds
- `ip-alignment-check`-tagged rules about specific framework
  positions

**Recording firings:**

```python
from _framework.learning import record_firing
record_firing(rule_id="<id>", skill_tag="ip-alignment-check",
              profile="{{KB_ID}}",
              action_summary="cited specific corpus doc per rule X")
```

## Action surface

- (L1 draft-only) — produces a verdict comment on a kanban task.
- (L4 structural-change) — when verdict is `gap`, may add a stub
  entry to the IP corpus marking what was missing (with a TODO for
  the principal to fill in).

## Verifier criteria

```yaml
verifier:
  - type: kanban_status
    args:
      task_id: "{{TASK_ID}}"
      status: "ready"   # status set when verdict is posted
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT * FROM task_comments WHERE task_id='{{TASK_ID}}' AND author='{{KB_ID}}'"
      expect_min: 1
```

## Failure modes

- **Verdict without citation** — claims `aligned` or `divergent`
  without naming a specific corpus document. Self-check catches it.
- **Producer drift** — skill starts writing the corrected version
  instead of naming the divergence. Hard rule: this skill never
  produces work product.
- **False `aligned`** — passing through a draft that misapplies the
  methodology. Catches at red-team (Analyst) review.

## Self-check

Before publishing the verdict:

1. Did I cite the specific corpus document? Not just "our framework"
   — the document.
2. Is my verdict one of the three (`aligned` / `divergent: <X>` /
   `gap: <Y>`)? Not "mostly" or "kind of."
3. If `divergent`: did I name the divergence specifically enough
   that the producer doesn't have to guess what to change?
4. If `gap`: did I capture the gap as a learning rule for the
   corpus? Gaps are corpus debt, tracked not just noted.
5. Am I producing instead of validating? If yes, stop and route to
   the appropriate producer.
