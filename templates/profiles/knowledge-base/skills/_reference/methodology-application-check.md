---
skill_id: methodology-application-check
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Methodology application check

Verifies that a proposed action correctly applies {{ORG_NAME}}'s
methodology. Different from `ip-alignment-check`: alignment asks
"does this match the framework"; methodology-application asks "is
the framework being applied in the right way, in the right order,
to the right kind of question."

## What this skill does

Given an artifact + the methodology it claims to apply:

1. Identify which methodology is in play
2. Check the methodology applies to this kind of question
   (wrong-tool-for-job is a divergence)
3. Walk the methodology's expected sequence; flag skipped or
   reordered steps
4. Identify edge-cases handled (or not handled)

Verdict: `correctly-applied` / `misapplied: <specifics>` /
`wrong-methodology: <which-methodology-fits>` /
`gap: <edge-case-not-handled>`

## Inputs

- Artifact (text or path)
- `methodology_claimed` (optional — if absent, KB infers from artifact)
- The methodology graph from `ip-curator`

## Supervised learning

Rules tagged `methodology-application-check`, `general`,
`role:knowledge-base`. Include methodology-specific "common
misapplication" rules.

## Action surface

- (L1) verdict comment on kanban task

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{KANBAN_DB}}"
      query: "SELECT body FROM task_comments WHERE task_id='{{TASK_ID}}' AND author='{{KB_ID}}'"
      expect_min: 1
```

## Failure modes

- **Methodology confusion** — applies Framework A's lens to a Framework
  B question. Self-check: which methodology did I identify, and why?
- **Step-skipping not flagged** — methodology has 5 steps, artifact
  uses 4, skipped step matters. Verifier checks that the verdict
  enumerates the expected steps.

## Self-check

1. Did I name which methodology I was checking against?
2. Did I list the expected steps + which were present + which were
   missing or reordered?
3. Is my verdict one of the four (correctly-applied / misapplied /
   wrong-methodology / gap)?
