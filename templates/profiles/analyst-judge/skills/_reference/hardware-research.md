---
skill_id: hardware-research
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
---

# Hardware research

Market research, price comparison, vendor discovery for hardware
purchase decisions. Plenty of agency owners face the same buy-
decisions (new laptop, server, peripherals, sound equipment) and
this saves them the research cycle.

## What this skill does

Given a hardware spec or use-case:

1. Identify candidate models matching the spec / use-case
2. Pull current pricing across vendors (B&H, Adorama,
   manufacturer direct, eBay for older models, etc.)
3. Cross-check against published reviews (with date weighting —
   2024 reviews of a 2024 product = strong signal; 2024 reviews
   of a 2019 product = stale)
4. Identify the load-bearing trade-offs ({{OWNER_NAME}} cares
   about X; this model is strong on X but weak on Y)
5. Produce a recommendation document: top-3 candidates with the
   trade-off analysis, prices, where-to-buy, when-to-buy
   (any imminent deals or new model launches that argue
   for waiting)

Output: a hardware-decision document delivered as a kanban task
for {{OWNER_NAME}}.

## Inputs

- `use_case` (text — what the hardware is for)
- `budget_ceiling` (optional)
- `constraints` (optional — quietness, size, compatibility, etc.)

## Supervised learning

Rules tagged `hardware-research`, `general`,
`role:analyst-judge`. {{OWNER_NAME}}'s preferences and prior
hardware experiences (what they liked, what they didn't) get
captured as learning rules.

## Untrusted content

Web-research content passes through prompt-injection scanner.
Reviews + spec pages are external; defensive content paraphrases
trigger patterns.

## Action surface

- (L1) — produce recommendation doc as kanban deliverable

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/hardware-decisions/{{DECISION_ID}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/hardware-decisions/{{DECISION_ID}}.md"
      needle: "Top 3 candidates:"
```

## Failure modes

- **Spec drift** — recommending products that don't actually meet
  the constraints. Self-check: did I tabulate constraints vs
  spec for each candidate?
- **Stale price** — quoted price out of date by hours. Always
  include "price as of <ts>" + "when this matters" guidance.
- **Single-vendor bias** — only considered Amazon. Hard rule: at
  least 2 vendors for any recommendation.

## Self-check

1. Did I check at least 2 vendors per candidate?
2. Did I date every cited review?
3. Did I name the load-bearing trade-off — what would change my
   recommendation?
4. Is there an imminent-event reason to wait (CES, manufacturer
   announcement, sale)?
5. Did I include "when to buy" guidance, not just "what to buy"?
