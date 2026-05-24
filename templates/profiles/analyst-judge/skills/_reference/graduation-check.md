---
skill_id: graduation-check
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
---

# Graduation check

Manual review path for autonomy promotion when the automated
graduation gate isn't enough. Provides the human-judgment layer when
a skill is operating in genuinely novel territory.

## What this skill does

For a skill flagged for graduation review:

1. Pull the skill's track record (last N runs, outcomes)
2. Read the audit findings (current + last 4 weeks of history)
3. Check learning fidelity (rules captured, firings, recaptures)
4. Hold the three-input gate alongside human judgment
5. Verdict: `promote` / `hold` / `demote` / `escalate-to-owner`

The `graduation_audit_gate.py` IS the automated path. This skill
exists as the override when the automation's signals are ambiguous
(e.g. skill recently changed scope, autonomy bar should be re-set).

## Inputs

- `skill` + `profile`
- Optional `reason` if the operator is explicitly requesting review

## Supervised learning

Rules tagged `graduation-check`, `general`, `role:analyst-judge`.

## Action surface

- (L1) — verdict as kanban comment + event emission

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{AUTONOMY_DB}}"
      query: "SELECT * FROM skill_autonomy_history WHERE skill='{{SKILL}}' AND profile='{{PROFILE}}' AND kind='graduation_check' ORDER BY ts DESC LIMIT 1"
      expect_rows: 1
```

## Failure modes

- **Rubber-stamping** — verdict comes back too quickly without
  reasoning. Self-check enforces a minimum.
- **Disagreeing with the automation without justification** —
  override the gate without naming what the gate missed.

## Self-check

1. Did I review all three gate inputs (track record + audit +
   learning fidelity)?
2. If I disagree with the gate's automated outcome: did I name what
   it missed?
3. Did I record the rationale in `skill_autonomy_history`?
4. If escalating to {{OWNER_NAME}}: did I write a specific question,
   not vague "please review"?
