---
skill_id: smart-goal-coach
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise, direct, warm-not-flattering]
---

# SMART goal coach

Q&A coaching to refine a vague aspiration into a SMART goal
(Specific, Measurable, Achievable, Relevant, Time-bound), then
drafting it into `Goals.md` with proposed interim milestones.

Pairs with `time-use-analyzer`: this skill *defines* what
matters; the analyzer *measures* whether time matches.

## What this skill does

Two modes — picked based on input:

### Mode A — Refine a new aspiration

Operator sends a vague goal: "I want to grow the business."
CoS runs the SMART check (via `_framework.goals.smart_check`),
identifies which dimensions are missing, and walks through
follow-up questions:

- **Specific:** "What specifically does 'grow the business' look
  like for you? More clients? Bigger contracts? New service line?"
- **Measurable:** "What number tells you it happened? Revenue
  threshold? Number of clients? Engagement count?"
- **Achievable:** "Given current capacity (you / specialists /
  systems), is this realistic in the window you're thinking?"
  (CoS doesn't pass-fail this — surfaces it for {{OWNER_NAME}}
  to assess)
- **Relevant:** "How does this connect to the mission in
  `Goals.md`? Or is this a new direction that warrants a mission
  update?"
- **Time-bound:** "By when? Specific date, end of quarter, end of
  year?"

After Q&A: draft the goal in SMART form, propose 3-4 interim
milestones (one per quarter or month, depending on the timeframe),
present to {{OWNER_NAME}} for confirmation, then write to
`Goals.md::The current year's goals` via
`_framework.goals.add_annual_goal()`.

### Mode B — Refine an existing goal

Operator picks an existing goal from `Goals.md` that's gone soft
or needs tightening. CoS runs `smart_check` on it, walks through
the missing dimensions, drafts the refined version, asks
"replace the current one with this?", and on confirmation uses
`replace_annual_goal()` to update the file.

## Inputs

- `aspiration` (text) — the vague version, OR
- `existing_goal_index` (int) — the index into `ANNUAL_GOALS` of
  the goal being refined

## Supervised learning

Rules tagged `smart-goal-coach`, `general`, `role:chief-of-staff`.
Per-operator calibration: which dimensions {{OWNER_NAME}} tends to
under-specify, preferred timeframe ranges, what counts as a
"good" interim milestone.

## Action surface

- (L1 draft-only) — Q&A coaching + proposed SMART goal + interim
  milestones, surfaced to {{OWNER_NAME}}
- (L4 structural-change) — after confirmation: write to `Goals.md`
  via `_framework.goals` helpers

## Verifier criteria

```yaml
verifier:
  - type: file_contains
    args:
      path: "{{GOALS_MD}}"
      needle: "{{NEW_GOAL_SNIPPET}}"
  - type: firing_recorded
    args:
      rule_id: "{{any SMART-related rule that fired}}"
      skill_tag: smart-goal-coach
```

## Failure modes

- **Premature commitment** — drafting a SMART goal before
  {{OWNER_NAME}} has resolved the underlying ambiguity ("what
  should I actually be optimizing for?"). Self-check: if more
  than one dimension is missing AND the operator's answers feel
  uncertain, pause and ask whether the aspiration is real or a
  not-yet-clear instinct.
- **Over-precise measurability** — turning "feel less burned out"
  into "score 8.5/10 on a wellbeing rubric I'll fill out
  weekly." Better: keep some goals deliberately qualitative; the
  SMART check warns but doesn't block.
- **Misalignment with mission** — a tactically SMART goal that
  isn't actually what the agency exists to do. Mode A's Relevance
  step catches this; if the operator answers "this isn't really
  in our mission but I want to do it anyway," that's the signal
  to update the mission, not just add the goal.
- **Interim-milestone busywork** — milestones that look like
  progress without being progress (e.g. "draft an outline" is a
  milestone toward a book; "complete a SWOT analysis" is usually
  a procrastination ritual). Self-check rejects vague milestones.

## Self-check

1. Did I run `smart_check` and surface the failing dimensions
   before drafting?
2. For each missing dimension: did I ask a specific follow-up,
   not a generic "tell me more"?
3. Are the interim milestones individually concrete (each is a
   thing-done, not a thing-planned)?
4. Did I get {{OWNER_NAME}}'s explicit confirmation before writing
   to `Goals.md`?
5. After writing: did I record firings for the rules that shaped
   the goal (timeframe-preference rule, interim-cadence rule, etc.)?
