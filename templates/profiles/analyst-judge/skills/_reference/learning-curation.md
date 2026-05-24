---
skill_id: learning-curation
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise, direct]
---

# Learning curation

Hygiene on the learning corpus. Dedupe, contradict-check, hardness
audit, tag-accuracy check. Never auto-commit; always write proposals
to the curation queue for {{OWNER_NAME}} review.

## What this skill does

Daily:

1. **Dedupe** — find rules with cosine similarity >0.95; propose
   merging
2. **Contradiction** — find rules that contradict each other; propose
   resolution (supersede one)
3. **Hardness audit** — find rules marked `is_hard=1` without a
   deterministic validator; propose demoting to soft
4. **Tag accuracy** — find rules tagged for skills where they've
   never fired; propose re-tag

Each proposal lands on the curation queue. Operator reviews + acts.
Never auto-commits.

## Inputs

- `learning.db`

## Supervised learning

Rules tagged `learning-curation`, `general`, `role:analyst-judge`.

## Action surface

- (L1) — write proposals to a queue
- (L4 structural-change) — when {{OWNER_NAME}} approves a proposal,
  execute it on the corpus

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/curation-queue/{{DATE}}.md"
```

## Failure modes

- **Over-aggressive dedupe** — proposes merging rules that should
  stay separate. Operator rejects; learning rule about the distinction.
- **Missed contradiction** — two rules in conflict, didn't notice.
  Owner correction → learning rule about the contradiction pattern.

## Self-check

1. Did I write to the queue (proposal), not directly to the corpus?
2. Did I cite specific evidence for each proposal (rule IDs,
   similarity scores)?
3. Did I batch similar proposals (don't flood the operator with 30
   separate dedupe suggestions)?
