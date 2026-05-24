---
skill_id: prompt-injection-defense
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Prompt injection defense

Adversarial security review of skills + scripts + inbound content
patterns. Identifies prompt-injection vulnerabilities; proposes
patches.

## What this skill does

Three modes:

1. **Audit a skill** — read its SKILL.md, identify if any external
   content passes through it, check for verbatim trigger quotes
   (`skill-injection-trigger` rule), suggest hardening.
2. **Audit a script** — same for cron scripts that handle external
   inputs.
3. **Synthetic attack** — given a skill, generate adversarial test
   inputs that might bypass its defenses.

Findings flow as kanban comments with severity ranking
(low/medium/high/critical).

## Inputs

- `target` — skill or script to audit
- `mode` — audit | synthetic-attack

## Supervised learning

Rules tagged `prompt-injection-defense`, `general`,
`role:analyst-judge`. Including new attack patterns as they emerge.

## Action surface

- (L1) — findings as kanban comments

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/injection-audits/{{TARGET_ID}}.md"
```

## Failure modes

- **Self-injection in my own audit** — I quote trigger phrases in my
  audit report verbatim. Hard rule: my OWN reports paraphrase.
- **Coverage gap** — new attack pattern I haven't seen. The
  ongoing rule curation captures these.

## Self-check

1. Did I paraphrase every trigger pattern in my own report?
2. Did I rank severity, not just list findings?
3. Did I propose specific patches, not just "this is vulnerable"?
4. Did I check for indirect injection (the skill loads X which loads Y
   which is the attack vector)?
