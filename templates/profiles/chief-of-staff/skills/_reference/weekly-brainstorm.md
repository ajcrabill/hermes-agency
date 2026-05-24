---
skill_id: weekly-brainstorm
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, precise]
---

# Weekly brainstorm

Every Sunday: produce **three specific, actionable ideas** for how
HermesAgency could autonomously help move further toward
{{ORG_NAME}}'s stated goals. Lands in the weekly review for
{{OWNER_NAME}} to triage (accept / defer / discard).

This is the agency proposing its own improvements. Not vague
"we could do more" — three concrete experiments {{OWNER_NAME}}
could greenlight.

## What this skill does

1. **Read context**:
   - `Goals.md` — what we're optimizing for
   - `goal_tracking.db` — current status per metric (at-risk +
     missed get priority attention in brainstorms)
   - Recent kanban activity — what's moved, what's stuck
   - Learning corpus — recurring corrections that point at
     systemic gaps
   - `time-use-analyzer`'s most recent drift report — where the
     calendar isn't matching priorities

2. **Generate three ideas** in three categories (one of each):
   - **New capability**: "build skill X to handle Y autonomously"
     (something the agency doesn't currently do)
   - **Pattern from corrections**: "the same correction has fired 5
     times — codify as hard rule + automate the response"
     (something we're learning to do faster)
   - **Resource re-allocation**: "Goal A is at-risk, and we have
     pattern Z draining time — propose dropping/automating Z to
     free hours for A" (something we could stop doing)

3. **Each idea includes**:
   - 1-sentence proposal
   - Which goal(s) it serves (from `Goals.md`)
   - Estimated implementation cost (hours / new skills / new
     integrations)
   - Why now (the specific signal that surfaced it)
   - First concrete step to validate

4. **Surface**: as a section in the weekly review with `tenant=goal-review`
   on the kanban task, so {{OWNER_NAME}} triages with the same
   discipline as any other inbound proposal.

## Inputs

- All of the agency's state (read-only): goals, metrics, kanban,
  learning corpus, time-use, prior brainstorm decisions
- Optional: kanban "discarded brainstorm ideas" tenant to avoid
  re-proposing things {{OWNER_NAME}} already rejected

## Supervised learning

Rules tagged `weekly-brainstorm`, `general`, `role:chief-of-staff`.
{{OWNER_NAME}}'s rejections become "don't propose this kind of
thing" rules; acceptances become "this kind of thing is on-mission."
Over time, the brainstorms get more precisely targeted.

## Action surface

- (L1 draft-only) — produce the three ideas as a kanban task in
  the weekly review

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/_health/weekly-brainstorm/{{WEEK_START}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/_health/weekly-brainstorm/{{WEEK_START}}.md"
      needle: "## Idea 3"
```

## Failure modes

- **Vague aspirations** — "improve productivity" or "grow faster"
  with no specific mechanism. Hard rule: every idea names a
  specific skill/integration/script + a first step.
- **Repetitive proposals** — same idea each week because the
  signal hasn't changed. Self-check: read last 4 weeks of
  brainstorms; if today's ideas overlap, re-derive instead of
  re-propose.
- **Politeness theater** — three "great" ideas with no real
  trade-offs. Hard rule: at least one idea this week should be
  about *stopping doing something* (not just starting).
- **Outside-of-mission scope creep** — proposing things
  {{ORG_NAME}} doesn't actually do. `Goals.md::EXPLICIT_NON_GOALS`
  is the filter — anything matching gets dropped pre-brainstorm.

## Self-check

1. Are all three ideas concrete (not abstract aspirations)?
2. Does each idea cite the specific signal that surfaced it
   (which at-risk goal, which recurring correction, which
   time-drift pattern)?
3. Does each idea name the first concrete step to validate?
4. Did I check `Goals.md::EXPLICIT_NON_GOALS` for filter-outs?
5. Did I check the rejected-ideas list for duplicates?
6. Is at least one idea about *stopping* something?
