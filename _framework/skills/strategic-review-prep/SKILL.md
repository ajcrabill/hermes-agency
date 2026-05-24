---
skill_id: strategic-review-prep
profile: __shared__
role: chief-of-staff
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
interim_goal: __cross__
outcome: __cross__
outcome_metric: |
  Principal walks into the quarterly review with the prior-quarter
  data summary + a question checklist within 24 hours of the
  trigger date.
status: green
alignment_argument: |
  This skill IS the quarterly top-tier test from StrategicPlanning.md
  §6.3 ("are these the right Outcomes?"). It's the layer of the
  testability model that asks the question only the Principal can
  answer. Cross-cuts every Outcome / Interim Goal / Initiative;
  cadence: quarterly (first Monday of Jan/Apr/Jul/Oct).
---

# Strategic-review-prep (quarterly)

The CoS's quarterly preparation for the Principal-led strategic
review meeting. Per StrategicPlanning.md §6.3, the top-tier test
asks a different question than the weekly health check:

  - **Weekly** (`strategic-plan-health-check`): "Are we
    implementing? Are we deploying resources wisely?"
  - **Quarterly** (this skill): "Do we have the *right*
    Outcomes?"

This skill produces the *data packet* the Principal walks into
the meeting with. The meeting itself is Principal-driven; the
CoS prepares, the Principal decides.

## When this skill fires

Cadence: **quarterly** — default first Monday of Jan / Apr / Jul / Oct.

  - Each week, the CoS profile's `quarterly-trigger-check` cron
    job calls `is_quarterly_trigger_day()`. On a True day, it
    invokes this skill.
  - Principal can also pull manually: *"give me the quarterly
    review packet"* or `/agency review-prep`.

## What's in the packet

Per StrategicPlanning.md §6.3:

1. **The plan, current state** — three-layer summary (Outcomes,
   Interim Goals, Initiatives) with status flags.

2. **Activity (last 90 days)** — total firings, top 5 most-active
   Initiatives by firing count. Tells the Principal where the
   agency actually spent its energy.

3. **Audit signals** — count of strategic-alignment findings by
   rule code. Tells the Principal where structural drift has
   accumulated.

4. **Principal-facing questions** — the §6.3 question set,
   tailored slightly by what the data shows:
   - Are these still the right Outcomes for this season?
   - Do the Interim Goals predict Outcome movement, or have
     they become proxies that no longer track the real thing?
   - Are there Outcomes the Principal is avoiding because
     they're uncomfortable to measure?
   - What did the past 90 days teach the plan didn't anticipate?
   - Which layer-1 (Outcomes / Guardrails) refinement should
     the CoS bring forward as a kanban proposal?

The packet is markdown, formatted for reading and marking up.

## How to invoke from Python

```python
from _framework.strategic_review import (
    produce_review_packet, render_packet,
    is_quarterly_trigger_day,
)
from datetime import date

# Schedule check
if is_quarterly_trigger_day(date.today()):
    packet = produce_review_packet()
    rendered = render_packet(packet)
    # Post to Principal's kanban inbox, save to vault, etc.
```

## Inputs

- None directly. Reads:
  - `Goals.md` (three-layer)
  - `~/.hermes/agency-state/_state/learning.db` (firings)
  - Audit findings (via `audit_deployment()`)

## Outputs

- A markdown review packet (~1-2 pages printed).
- Designed to be marked up — the Principal brings it to the
  review meeting and notes their answers next to the questions.
- The review *itself* may produce a layer-1 refinement proposal
  (Outcomes / Guardrails change); that gets filed via the
  `goals-revision-proposal` flow (v0.23.x next-step).

## Supervised learning

Rules tagged `strategic-review-prep`, `chief-of-staff`. Per-Principal
calibration for: which questions resonate; whether to include
non-business Outcomes prominently; how much firings-rollup detail
to show.

## Action surface

- (L1 draft-only) — reads vault docs + DBs, produces markdown.
  Never mutates Goals.md or any skill file.

## Verifier criteria

```yaml
verifier:
  - type: report_structure
    args:
      sections_required:
        - "The plan (current state)"
        - "Activity (last 90 days)"
        - "Audit signals"
        - "Questions to bring to the review meeting"
      reads_only: true
```

## Failure modes

- **No three-layer plan** — packet returns a "no plan to review"
  message pointing at `/agency setup`. Don't silently produce
  an empty packet.
- **Zero firings recorded** — the packet calls this out as a
  diagnostic question (is work not happening, or not being
  logged?). Don't hide it.
- **Quarterly cron miss** — if the cron misses the first Monday
  (machine off, etc.), the next-Monday catch is acceptable. The
  Principal cares about quarterly cadence, not pixel-perfect
  scheduling.

## Self-check

1. Did the packet include all four sections (plan / activity /
   audit / questions)?
2. Were the questions concrete + decision-oriented (not vague
   "how do you feel about the plan")?
3. Did I avoid making the Principal's decisions for them in the
   packet's framing? (The CoS prepares; the Principal decides.)
4. Did the packet fit in ~1-2 pages printed?
