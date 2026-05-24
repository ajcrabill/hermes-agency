---
skill_id: structural-edit
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Structural edit

First of three sequential editor lenses. Evaluates a chapter draft
for structural integrity — logical flow, missing arguments,
transitions, pacing, repetition, chapter purpose. Returns scored
verdict (0.0-1.0, target ≥0.90 to pass to the voice editor).

## What this skill does

Given a chapter draft + optional project context:

For each item, score 0.0-1.0 and explain:

1. **Logical flow** — does the argument progress without leaps?
2. **Missing arguments** — gaps where a step in reasoning is skipped?
3. **Transitions** — smooth or jarring?
4. **Pacing** — consistent? Too fast / too slow?
5. **Repetition** — points made more than once without intentional
   reinforcement?
6. **Chapter purpose** — does the chapter deliver on its implied
   thesis?

Returns: chapter id, overall structural score, per-item scores,
specific revisions cited with line/paragraph references.

Does NOT fix grammar or change voice. That's the next two passes
(`voice-edit` then `polish-edit`). One lens per skill keeps the
verdicts crisp.

## Inputs

- `chapter_text` (or `chapter_path`)
- `project_id` (optional — loads coaching.db for project context)

## Supervised learning

Rules tagged `structural-edit`, `general`, `role:writing-support`.
Per-methodology rules calibrate "what good structure looks like for
this kind of book."

## Action surface

- (L1) — verdict as kanban comment + structured JSON in
  `deliverables` table

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{COACHING_DB}}"
      query: "SELECT * FROM deliverables WHERE project_id={{PROJECT_ID}} AND name LIKE 'structural-edit:%' ORDER BY version DESC LIMIT 1"
      expect_rows: 1
  - type: file_contains
    args:
      path: "{{DELIVERABLE_PATH}}"
      needle: "Structural Score:"
```

## Failure modes

- **Score inflation** — every chapter gets 0.95+. Self-check:
  variance reasonable across recent reviews?
- **Drift into voice** — flagging "this isn't how I'd say it" as a
  structural issue. Hard rule: voice is the next pass, not mine.
- **Vague verdict** — "needs work" without cited line. Hard rule:
  every observation references specific text.

## Self-check

1. Did I score each of the 6 items independently?
2. For each score below 0.85: did I cite the specific failure mode?
3. Did I stay in the structural lens — not commenting on voice or
   grammar?
4. Is my overall score the lowest of the 6 (not an average)?
