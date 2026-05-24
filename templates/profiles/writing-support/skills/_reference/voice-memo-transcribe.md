---
skill_id: voice-memo-transcribe
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Voice memo transcribe

When an author sends a voice memo as an attachment (.m4a / .mp3 /
.wav / .ogg / etc.), transcribe it to text using local STT (faster-
whisper by default — operator-configurable). Hand the transcript
back to `manuscript-ingest` so the rest of the coaching pipeline
treats it the same as a typed response.

## What this skill does

1. Receive an audio file path
2. Run STT (faster-whisper by default; operator can swap backends)
3. Return the transcript with confidence flags per segment
4. Mark low-confidence segments for author review rather than guess

The framework doesn't bundle the STT model. Operator installs
`faster-whisper` (or chosen alternative) at deployment time. Without
the STT backend, this skill emits a `voice_memo_skipped` event +
files a kanban task asking the operator to install it.

## Inputs

- `audio_path` — absolute path to the file
- `expected_speaker` (optional) — author's name, helps the
  transcriber

## Supervised learning

Rules tagged `voice-memo-transcribe`, `general`,
`role:writing-support`. Includes calibration notes (e.g. "this
author tends to pause for 2-3 seconds between thoughts; segment
on that").

## Action surface

- (L1) — produce transcript file + return path

## Untrusted content

Audio is external content. The transcript passes through the
prompt-injection scanner before being passed downstream.

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{TRANSCRIPT_PATH}}"
  - type: file_contains
    args:
      path: "{{TRANSCRIPT_PATH}}"
      needle: "[transcribed:"
```

## Failure modes

- **STT backend missing** — `import faster_whisper` fails. Skill
  emits skipped-event + files operator task. Does NOT block the
  rest of the workflow.
- **Bad audio** — clipped, noisy, silent. Transcript will be sparse;
  low-confidence flag tells `manuscript-ingest` to surface for
  review rather than process as content.
- **Wrong language** — author switched languages mid-memo. Auto-
  detect; emit a `voice_memo_mixed_language` event if confidence
  drops mid-stream.

## Self-check

1. Did I include confidence-per-segment in the output?
2. For low-confidence segments (<0.7): did I mark them rather than
   silently include them?
3. Did I store the transcript at a predictable path so
   `manuscript-ingest` finds it?
