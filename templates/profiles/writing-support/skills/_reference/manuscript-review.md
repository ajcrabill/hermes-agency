---
skill_id: manuscript-review
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Manuscript review

Feedback on author drafts (a chapter or the full manuscript).
Structure-first, then prose. Calibrated to the author's voice
profile.

## What this skill does

Given a draft:

1. Read all of it before commenting on parts
2. Structure pass — does the arc work? Are chapters in the right
   order? Is the through-line clear?
3. Per-chapter pass — what's the chapter doing? Does it earn its
   place? Is the chapter's argument clear?
4. Line pass — sentences, paragraphs, voice consistency
5. Voice-fidelity check — is the author's voice consistent throughout?

Feedback comes back as a structured doc, then a kanban-comment summary
for CoS to relay to the author (in CoS's voice + the author's tone
calibration).

## Inputs

- Manuscript file + author_id

## Supervised learning

Rules tagged `manuscript-review`, `general`, `role:writing-support`.
Per-author voice profile loaded from `multi-author-state`.

## Action surface

- (L1) — review document + kanban summary

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/reviews/{{MANUSCRIPT_ID}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/reviews/{{MANUSCRIPT_ID}}.md"
      needle: "## Structure"
```

## Failure modes

- **Structure-skipping** — went straight to line edits without
  the arc pass. Self-check forces sequence.
- **Voice substitution** — review reads as wanting the author to
  sound like me. Voice-profile check against samples.
- **Vagueness** — "tighten this" with no cited line. Hard rule:
  every observation cites a line or paragraph.

## Self-check

1. Did I read the whole thing before commenting on parts?
2. Did I do the structure pass FIRST?
3. Did I cite specific lines for every observation?
4. Is my feedback in service of the author's voice, not mine?
