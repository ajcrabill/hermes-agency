---
skill_id: prior-decision-search
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Prior decision search

"Have we decided something like this before?" Semantic search across
the agency's decision log + IP corpus + prior client engagements.

## What this skill does

Given a question or proposed decision:

1. Search the decision log (`Clients.md::CLIENT_SPECIFIC_RULES`,
   IP corpus decisions, `operational-state.md::Recent operator decisions`)
2. Find semantically similar prior decisions
3. Return: the prior decision text + the context where it was made +
   the date + the outcome (if recorded)
4. Flag any prior decisions that would CONTRADICT the proposed
   action (especially valuable)

Output is informational — KB doesn't make the new decision, just
surfaces what's been decided before.

## Inputs

- The question or proposed decision
- `search_scope` (optional) — limit to specific corpus areas

## Supervised learning

Rules tagged `prior-decision-search`, `general`. Calibration rules
about similarity threshold (too loose → false matches; too tight →
miss true matches).

## Action surface

- (L1) returns search results as a kanban comment or direct output

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/decision-search/{{QUERY_HASH}}.md"
```

## Failure modes

- **False negative** — relevant prior decision exists but search
  missed it. Owner correction; rule about better search query
  formulation.
- **False positive** — surfaced an unrelated prior decision as
  similar. Less harmful (recipient discards) but pollutes signal.

## Self-check

1. Did I search the decision log AND IP corpus AND state-vault?
2. Did I flag any contradictions explicitly?
3. Did I include the date + context of each match?
4. If no matches: did I say so clearly rather than fabricating?
