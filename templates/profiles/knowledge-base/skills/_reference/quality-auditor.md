---
skill_id: quality-auditor
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Quality auditor

Second-tier verdict on work-product quality. Composes with
AnalystJudge's adversarial review and {{ORG_NAME}}'s alignment
check — provides the quality-of-execution lens.

## What this skill does

Given a work product (draft, deliverable, response):

1. Score on continuous scales (not pass/fail): clarity (0-1),
   specificity (0-1), evidence-grounding (0-1), accessibility (0-1)
2. Identify the lowest-scoring dimension as the one to fix first
3. Suggest specific improvements (with cite-the-line)
4. Compose with `ip-alignment-check` (KB) and `red-team` (Analyst) —
   three independent lenses on the same artifact

Auto-undelegation pattern (from agent-core): if a producer's
quality score trends downward over their last 5 outputs, surface
to {{OWNER_NAME}} for redirection.

## Inputs

- The work product
- The producer (which specialist made it)
- `expected_quality` threshold (defaults to 0.7 across dimensions)

## Supervised learning

Rules tagged `quality-auditor`, `general`. Include dimension-
calibration rules (what "specificity 0.8" actually means for this
agency).

## Action surface

- (L1) verdict + scores as kanban comment

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/quality-audits/{{ARTIFACT_ID}}.json"
```

## Failure modes

- **Scoring drift** — same artifact gets different scores on
  re-evaluation. Mitigation: log scores with their reasoning so
  patterns surface.
- **All-pass theater** — every artifact scores 0.9+. Self-check:
  if my last 10 audits all said "great," am I actually evaluating
  or rubber-stamping?

## Self-check

1. Did I score each dimension independently (not one halo score)?
2. For each low score: did I cite specific lines?
3. Is my variance reasonable (not all 0.9s, not all 0.4s)?
4. If trend is downward for a producer: did I surface to {{OWNER_NAME}}?
