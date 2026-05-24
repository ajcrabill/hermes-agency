---
skill_id: polish-edit
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Polish edit

Final of three sequential editor lenses. After structural (0.90+)
and voice (0.90+) passes, the polish editor catches what the prior
lenses didn't: grammar, punctuation, sentence clarity, formatting,
consistency. Target ≥0.90 to mark ready-for-author-review.

## What this skill does

The mechanical pass. Per the chapter draft:

1. **Grammar** — subject-verb agreement, verb tense consistency,
   pronoun agreement
2. **Punctuation** — commas, periods, quotes, dashes, all used
   correctly and consistently
3. **Sentence clarity** — confusing, overly long, ambiguous sentences
4. **Word choice** — better/clearer/more precise words (not vocabulary
   upgrades — removing wrong or confusing words)
5. **Formatting** — heading styles, paragraph breaks, list
   formatting, emphasis (bold/italic) consistent
6. **Consistency** — same terms used throughout (e.g., "board member"
   not "boardmember" then "board member")

Does NOT change voice (already passed) or restructure (already
passed). Mechanical only.

## Inputs

- `chapter_text` (or `chapter_path`)
- `project_id` (optional)

## Supervised learning

Rules tagged `polish-edit`, `general`, `role:writing-support`.
Per-project style rules (e.g. Oxford comma usage, term
conventions) load here.

## Action surface

- (L1) — verdict as kanban comment + JSON in `deliverables`

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{COACHING_DB}}"
      query: "SELECT * FROM deliverables WHERE project_id={{PROJECT_ID}} AND name LIKE 'polish-edit:%' ORDER BY version DESC LIMIT 1"
      expect_rows: 1
```

## Failure modes

- **Stylistic preference vs error** — flagging legitimate variation
  as wrong. Hard rule: flag only when an error or inconsistency,
  not personal preference.
- **Voice damage** — "fixing" prose that was deliberately
  unconventional (rhetorical fragments, dialect, etc.). Cross-check:
  did voice-edit approve this exact passage?
- **Missed obvious typo** — over-focused on subtle issues, missed
  basic ones. Self-check: did I run a basic typo scan first?

## Self-check

1. Did I check that structural-edit + voice-edit passed first?
2. For each score below 0.90: did I cite the specific
   error/inconsistency?
3. Did I stay in the mechanical lens — no structural or voice
   commentary?
4. Did I distinguish actual errors from personal preference?
5. Is my overall score the lowest of the 6?
