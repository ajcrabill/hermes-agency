---
skill_id: research
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
---

# Research

General research skill — vault + web + prior decisions — grounded in
agency goals. Different from `dossier-builder` (which is people-
focused); this is topic / question / decision-support research.

## What this skill does

Given a research question:

1. Search vault first (agency-vault, profiles' context dirs, IP corpus)
2. Search web second (with prompt-injection scanner on results)
3. Reconcile findings (where they agree, where they disagree)
4. Surface the load-bearing evidence + what would change my mind
5. Confidence-score the findings; <0.8 says so

Output is a research brief + source list + confidence flags.

## Inputs

- `question` — what to research
- `scope` — vault-only / web / both
- `due_by` — affects depth

## Supervised learning

Rules tagged `research`, `general`, `role:analyst-judge`.

## Untrusted content

Web results are external. Scanner runs. Paraphrase patterns.

## Action surface

- (L1) — produce research brief

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/research/{{QUERY_HASH}}.md"
```

## Failure modes

- **Confirmation bias** — only sources I agree with cited. Self-check:
  did I find sources that argue against?
- **Outdated source** — 2018 article on a fast-moving topic.
  Date everything; flag staleness.

## Self-check

1. Did I search vault before web?
2. Did I cite at least one source that argues against my conclusion?
3. Did I confidence-score each major claim?
4. Did I name what would change my mind?
