---
skill_id: newsletter-drafting
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Newsletter drafting

Weekly newsletter. One thing per week, focused, in the agency's
voice (not Writing's). Drafted by Wednesday, in CoS's queue by
Thursday.

## What this skill does

For each week:

1. Pull candidate topics (from editorial calendar +
   `operational-state.md::Recent operator decisions` + recent
   newsworthy moments)
2. Pick ONE topic. Not a roundup.
3. Draft in CoS's voice (because she's the agency to the world).
   Writing crafts the prose; CoS owns the voice the world sees.
4. KB checks IP alignment
5. Analyst red-teams (especially fact-checking)
6. CoS reviews + sends

## Inputs

- Editorial calendar
- Recent activity (operator decisions, BD wins, content output)
- Topic queue

## Supervised learning

Rules tagged `newsletter-drafting`, `general`, `role:writing-support`.
Particularly: voice-fidelity rules (the newsletter sounds like CoS,
not like Writing).

## Action surface

- (L1) — draft → KB + Analyst → CoS

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/newsletter/{{WEEK_START}}.md"
  - type: kanban_status
    args:
      task_id: "{{KB_REVIEW_TASK_ID}}"
      status: done
```

## Failure modes

- **Multi-topic drift** — newsletter becomes a roundup. Hard rule:
  one topic. Self-check rejects if >1 H2.
- **Voice substitution** — Writing's voice creeps in. Voice profile
  for CoS loaded at draft time.
- **Late delivery** — newsletter goes out Friday because Thursday
  drafting started Thursday. Hard rule: drafted by Wednesday.

## Self-check

1. Is there ONE topic, not three?
2. Does this sound like CoS, not me (Writing)?
3. Did KB sign off on alignment?
4. Did Analyst red-team for factual claims?
5. Is it in CoS's queue by Thursday?
