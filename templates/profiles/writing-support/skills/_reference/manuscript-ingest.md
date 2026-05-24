---
skill_id: manuscript-ingest
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Manuscript ingest

The capture mechanism. When an author submits a .docx, .pdf, .txt,
or voice memo, this skill (via the script `ingest-attachments.py`)
downloads the attachment, extracts text, computes sha256 for dedup,
and stores the result in `coaching.db::ingested_files` linked to the
author's project.

For voice memos, hands off to `voice-memo-transcribe` first, then
ingests the transcript.

## What this skill does

Mechanical layer:

1. Receive a message_id + author_email (from CoS via kanban after
   inbox triage routed it here)
2. Look up the author's active project in coaching.db
3. For each attachment:
   - Compute sha256
   - Check `ingested_files.sha256` — if present, log a dedup-hit
     event and skip
   - For .docx: extract text (incl. tables, headers, footers)
   - For .pdf: extract text via pdftotext
   - For .txt: read directly
   - For .m4a/.mp3/.wav: hand to `voice-memo-transcribe` skill
   - Store extracted text at
     `context/writing-support/projects/<short-name>/raw/<sha256>.txt`
   - Insert ingested_files row with chars + extracted_path
4. If the extracted text appears to be an answer to outstanding
   coaching questions, hand the parsed answers to `coaching-method`
   for matching

## Inputs

- `message_id`
- `author_email`

## Supervised learning

Rules tagged `manuscript-ingest`, `general`, `role:writing-support`.

## Action surface

- (L1) — produce ingested_files rows + extracted text on disk
- (L4 structural-change) — DB writes

## Untrusted content

Attachments are external. Extracted text passes through
prompt-injection scanner before being incorporated into coaching
context. Defensive content paraphrases trigger patterns.

Files that fail to extract cleanly (corrupted, password-protected,
unsupported format) emit a `manuscript_ingest_failed` event with
the failure reason; original message stays on the kanban for owner
triage.

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{COACHING_DB}}"
      query: "SELECT * FROM ingested_files WHERE source_msg_id='{{MSG_ID}}'"
      expect_min: 1
```

## Failure modes

- **Silent corruption** — extract returns garbled text but no
  exception. Mitigation: chars < 100 → flag for review.
- **Wrong-project attribution** — author has multiple active
  projects + the email doesn't disambiguate. Flag for owner triage.
- **Voice-memo size** — large recording timing out the transcribe
  pipeline. Chunk + retry; flag if still failing.

## Self-check

1. Did I dedup against `sha256` before writing?
2. Did I store the extracted text in the project's raw/ dir?
3. Did I link to the right `project_id`?
4. For unsupported file types: did I fail gracefully + emit the
   event with a clear reason?
