---
skill_id: shopping-research
profile: {{ANALYST_ID}}
role: analyst-judge
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, direct]
---

# Shopping research

Market research + price comparison + buy/wait guidance for any
purchase {{OWNER_NAME}} is considering. Hardware, software,
furniture, professional services, gear, gifts — same pattern: ask
what they want, ask what they'll pay, scour the world, deliver
top candidates with the trade-offs named.

## What this skill does

The interview-then-search pattern:

### Step 1 — Specifics interview

Ask {{OWNER_NAME}} (or extract from their kanban task body):

- **What are you looking for?** (More detail is better — model
  numbers, brand preferences, specific features, use-cases.)
- **Min/max price?** Floor + ceiling. Floor matters: cheaper than
  X usually means corner-cut.
- **Constraints?** Form factor, weight, color, dimensions,
  compatibility, delivery timeline, ethical (made-where, certified-
  what), warranty needs.
- **What will you use it for?** Use-case shapes "the right model"
  more than spec sheets.
- **Replacing something?** What did the prior version do right /
  wrong? Strong signal.

### Step 2 — Search

Scour:

- Manufacturer direct (often best price + warranty)
- Major marketplaces (Amazon, B&H, Adorama, eBay for older models,
  Wirecutter / Consumer Reports / RTINGS / specialist review sites)
- Discount channels (refurbished, open-box, last-gen models on
  closeout)
- Niche-vendor sources for the specific category

For services: same shape — directories, reviews, peer recommendations,
specialty professionals.

### Step 3 — Recommend

Top 3 candidates, each with:

- Spec match against the interview (constraints met / unmet)
- Current price + best vendor (with date stamp — prices move)
- Reviews summary (weighted by recency)
- Trade-off named ("strong on X but weak on Y — matters for you
  because Z")
- When to buy (now / wait — any imminent sales, model refreshes,
  or seasonal patterns)

## Inputs

- `request` — text describing what's wanted (often a kanban task
  body)
- Or interactive: skill walks through the specifics interview

## Supervised learning

Rules tagged `shopping-research`, `general`, `role:analyst-judge`.
{{OWNER_NAME}}'s preferences and prior buy/regret experiences get
captured as learning rules ("I always end up wanting the 'nicer'
version — start at +20% of stated budget" type calibrations).

## Untrusted content

Web research content passes through prompt-injection scanner.
Reviews + spec pages + price pages are external; defensive content
paraphrases trigger patterns.

## Action surface

- (L1) — produce recommendation doc as kanban deliverable

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/shopping-research/{{REQUEST_ID}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{ANALYST_ID}}/context/{{ANALYST_ID}}/shopping-research/{{REQUEST_ID}}.md"
      needle: "Top 3"
```

## Failure modes

- **Spec drift** — recommending options that miss the stated
  constraints. Self-check: tabulate constraints vs spec for each
  candidate.
- **Single-vendor bias** — only checked Amazon. Hard rule: ≥ 2
  vendors per candidate.
- **Stale price** — price quoted hours ago is now wrong. Always
  date the price + note volatility (electronics shift weekly;
  furniture shifts seasonally).
- **Wrong "use it for"** — recommending a pro tool to a hobbyist
  (over-spec'd, over-priced) or vice versa. Always tie the
  recommendation to the use-case.

## Self-check

1. Did I do the specifics interview before searching? (Bad searches
   come from underspecified questions.)
2. Did I check ≥ 2 vendors per candidate?
3. Did I date every cited price + review?
4. Did I name the load-bearing trade-off per candidate?
5. Did I include "when to buy" guidance, not just "what to buy"?
6. If the stated min/max didn't match the use-case, did I flag the
   mismatch rather than silently exceed the budget?
