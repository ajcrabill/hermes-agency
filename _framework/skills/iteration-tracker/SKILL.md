---
skill_id: iteration-tracker
profile: __shared__
role: __cross_role__
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# Iteration tracker

Records every feedback round on any artifact + surfaces stuck
loops. Generic — works for prototypes, but also for any other
iterative work (verifier criteria authoring, audit rule tuning,
graduation review).

## What this skill does

Three operations:

1. **Record a round** — given an artifact + the feedback received,
   capture what changed in the next version + which reviewer the
   feedback came from.

2. **Surface convergence** — query the round history. Decreasing
   feedback length over recent rounds = converging. Stable / growing
   feedback length = not converging.

3. **Surface stuck loops** — if N rounds have happened without
   shipping AND feedback isn't shortening AND only one reviewer
   has been involved, flag the loop as likely-stuck and propose:
   - Ship as-is and learn from production
   - Invite a different reviewer (KB / Analyst / Owner-direct)
   - Restart from a different example set

## Inputs

- `artifact_id` — the thing being iterated (prototype id, draft
  path, kanban task id, etc.)
- `feedback` — the feedback received this round
- `change_summary` — what changed in response
- `feedback_source` — owner / kb / analyst / self / specific person

## Supervised learning

Rules tagged `iteration-tracker`, `general`. Per-operator patience
calibration ("after round 4 with no clear convergence, flag" vs
"after round 7").

## Action surface

- (L1 draft-only) — read iteration state
- (L4 structural-change) — write rounds to prototypes.db (or
  caller-specified DB)

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{PROTOTYPES_DB}}"
      query: "SELECT * FROM prototype_rounds WHERE prototype_id={{PROTOTYPE_ID}} ORDER BY round_number DESC LIMIT 1"
      expect_min: 1
```

## Failure modes

- **Recording rounds that aren't actually new** — same draft + same
  feedback recorded twice. Dedup by `(prototype_id, round_number)`
  uniqueness.
- **False "stuck" alarm** — operator is making rapid progress that
  the diagnostic misreads. Operator can mark a prototype as
  `actively-converging` to suppress the alarm for N rounds.
- **Single-reviewer blind spot** — operator alone has approved 5
  rounds. Even if "converging," the absence of a second viewpoint
  is itself a risk. Surface as a soft suggestion, not a block.

## Self-check

1. For every recorded round: is the change_summary specific (not
   "general improvements")?
2. After 3+ rounds: did I run convergence_diagnostic at least once?
3. If the diagnostic returned "likely stuck": did I surface to the
   operator with concrete options, not just an alert?
