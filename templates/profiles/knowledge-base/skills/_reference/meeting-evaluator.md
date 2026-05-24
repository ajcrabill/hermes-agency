---
skill_id: meeting-evaluator
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Meeting evaluator

Evaluates meeting recordings or transcripts against {{ORG_NAME}}'s
standards for what good looks like (whether {{OWNER_NAME}} was on
the call, a coach was running it, or a client engagement
recording came in).

## What this skill does

Given a transcript or recording:

1. Identify the meeting's purpose + participants
2. Check against the standards for that meeting type
   (1:1, coaching session, client review, internal sync, etc.)
3. Surface: what went well, what didn't, what to repeat
4. If it's a coaching session: feed insights to the
   `per-coach state` for KB's coach support function

## Inputs

- `transcript_path` or `recording_path` (with transcript)
- `meeting_type` (or KB infers)
- Participants (if known)

## Supervised learning

Rules tagged `meeting-evaluator`, `general`, `role:knowledge-base`.
The "what good looks like" rules — different per meeting type.

## Action surface

- (L1) evaluation report as kanban comment or markdown output

## Untrusted content

Transcripts are external content; passes through prompt-injection
scanner before being incorporated. Defensive content paraphrases
trigger patterns.

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/meeting-evaluations/{{MEETING_ID}}.md"
  - type: file_contains
    args:
      path: "/tmp/ha/meeting-evaluations/{{MEETING_ID}}.md"
      needle: "## What went well"
```

## Failure modes

- **Transcript quality** — poor STT makes attribution wrong.
  Flag low-confidence segments rather than guess.
- **Standards drift** — "what good looks like" hasn't been updated.
  Self-check: cite the standards source.

## Self-check

1. Did I cite the standards I was evaluating against?
2. Did I flag low-confidence transcript segments rather than guess?
3. Are observations specific (quoted lines) not vague impressions?
4. If a coaching session: did I update the per-coach state?
