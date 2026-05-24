---
skill_id: weekly-review
profile: {{COS_ID}}
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only, send-batched]
voice_tags: [direct, we-not-i]
---

# Weekly review

Sunday-morning recap of the week. Goals progress, said-vs-done
audit, system health, what to repeat, what to change.

## What this skill does

Compose the weekly review covering:

- **Goals progress** — for each item in `Goals.md::ANNUAL_GOALS`,
  what shifted this week
- **Active projects** — for each in `Goals.md::ACTIVE_PROJECTS`,
  the current phase + what's needed next week
- **Said-vs-done audit** — what CoS committed to, what actually
  shipped, what slipped
- **System health** — Sentinel's compliance report summary
- **Pipeline truth** — BD's weekly opportunity scan
- **Editorial cadence** — Writing's newsletter / publications
- **What to repeat / what to change** — one of each (forces
  reflection)

Delivered Sunday morning. Drives Monday-morning prioritization.

## Inputs

- Goals.md + Values.md (the agency's standards)
- Kanban week-summary
- Sentinel's compliance report
- Per-specialist weekly outputs

## Supervised learning

Rules tagged `weekly-review`, `general`, `role:chief-of-staff`.

## Action surface

- (L1) draft
- (L2) send Sunday batch

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "/tmp/ha/weekly-reviews/{{WEEK_START}}.md"
  - type: file_contains
    args:
      path: "/tmp/ha/weekly-reviews/{{WEEK_START}}.md"
      needle: "Said-vs-done"
```

## Failure modes

- **Politeness theater** — review reads as victorious when the week
  wasn't. Said-vs-done forces honesty; verifier checks for the section.
- **Goal-drift** — review doesn't tie back to Goals.md. Self-check
  catches it.

## Self-check

1. Did I cite every active goal explicitly?
2. Did I name what didn't ship as bluntly as what did?
3. Is the "what to change" actionable (specific change, not vague)?
4. Did I include the compliance flag from Sentinel?
