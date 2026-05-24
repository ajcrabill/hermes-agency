---
skill_id: multi-author-state
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Multi-author state

Maintains per-author state. Voice profile, project arc, coaching
history, momentum status. Updated by `book-coaching`,
`manuscript-review`, and any author touch.

## What this skill does

Per author, in `context/writing-support/authors/<author-id>/`:

- `voice.md` — distillation of voice from sample text (sentence
  rhythm, vocabulary, register)
- `project.md` — book title + topic + current phase
- `arc.md` — outline + word count + chapter status
- `history.md` — coaching exchanges + manuscripts received + responses
- `momentum.json` — last touch date, days since, projected
  next-touch

The skill itself is the I/O for these files. Other skills read from
them; this skill updates them.

## Inputs

- `author_id`
- Event to log (coaching exchange / manuscript / status change)

## Supervised learning

Rules tagged `multi-author-state`, `general`, `role:writing-support`.
Per-author voice rules are loaded by `book-coaching` from the
voice.md file this skill maintains.

## Action surface

- (L1) — propose state updates
- (L4 structural-change) — write to per-author files

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/authors/{{AUTHOR_ID}}/momentum.json"
```

## Failure modes

- **Cross-author leak** — author A's voice notes leak into author B's
  files. Hard rule: every write is path-namespace-checked.
- **Stale momentum** — momentum.json doesn't update on a real touch.
  Verifier checks the timestamp moved.
- **History sprawl** — history.md grows unboundedly. Quarterly
  archive to `history-{{YYYYQ}}.md`.

## Self-check

1. Did I write to the right author's path? (`<author>/...`)
2. Did I update momentum.json after the state change?
3. Is voice.md grounded in samples (not my impressions)?
4. If history.md > 1MB, did I archive?
