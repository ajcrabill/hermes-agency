---
skill_id: voice-edit
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Voice edit

Second of three sequential editor lenses. After the structural pass
(0.90+), checks the chapter sounds like the author — natural,
consistent, authentic. Returns scored verdict (target ≥0.90 to pass
to the polish editor).

## What this skill does

Given a chapter that passed the structural pass:

Per author's voice profile from `multi-author-state` (or inferred
from the draft's natural patterns), score 0.0-1.0:

1. **Natural tone** — reads like someone talking to a friend, or a
   textbook?
2. **Consistent voice** — same throughout, or shifts formal ↔ casual?
3. **Authenticity** — real human experience, or generic advice?
4. **Over-editing** — has it been polished into clean-but-personality-
   less prose?
5. **Direct address** — does the author speak to the reader where it
   fits?
6. **Storytelling** — concrete stories + examples, or just
   abstractions?

Returns: chapter id, voice score, per-item scores, specific lines
that drift from the author's voice.

## Inputs

- `chapter_text` (or `chapter_path`)
- `project_id` — required (loads voice profile from
  `multi-author-state`)

## Supervised learning

Rules tagged `voice-edit`, `general`, `role:writing-support`.
Per-author voice rules load from
`context/writing-support/authors/<author>/voice.md`.

## Action surface

- (L1) — verdict as kanban comment + JSON in `deliverables`

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{COACHING_DB}}"
      query: "SELECT * FROM deliverables WHERE project_id={{PROJECT_ID}} AND name LIKE 'voice-edit:%' ORDER BY version DESC LIMIT 1"
      expect_rows: 1
```

## Failure modes

- **My voice instead of the author's** — observations reflect my
  taste, not author voice fidelity. Hard rule: voice profile cited
  in every observation.
- **Pre-mature pass** — accepting voice issues that voice-profile
  samples would have flagged. Self-check: did I actually compare
  against samples?
- **Cross-author leak** — author A's voice patterns applied to
  author B's draft. Namespace guard in per_subject_state catches.

## Self-check

1. Did I load the voice profile from this author's `voice.md`?
2. For each score below 0.85: did I cite a sample line from the
   profile alongside the divergent draft line?
3. Did I stay in the voice lens — not flagging structural or
   grammar issues?
4. Is my overall score the lowest of the 6?
