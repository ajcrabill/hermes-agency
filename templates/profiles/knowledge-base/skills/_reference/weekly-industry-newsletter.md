---
skill_id: weekly-industry-newsletter
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, voice-aware]
cadence: weekly
trigger: friday-am
---

# Weekly industry newsletter

A personalized intelligence brief delivered to {{OWNER_NAME}} every
Friday morning. Distills KB's understanding of {{OWNER_NAME}}'s
industry, goals, IP, interests, and thought-leadership areas — then
scours the past seven days of the world for relevant information and
drafts a curated newsletter.

This skill is *not* a generic industry-news scraper. It's a
KB-authored brief that knows what {{OWNER_NAME}} cares about, what
{{OWNER_NAME}} already knows (so it doesn't repeat), and what's
worth surfacing.

## What this skill does

Once per week (Friday AM by default):

1. **Pull principal context** — read Goals.md, Values.md, Work.md,
   Personal.md, Clients.md from the agency vault. Read the IP corpus
   tags `interests`, `thought-leadership-areas`, `industry-focus`.
2. **Build a query plan** — turn each focus area into 2-4 search
   queries that bias toward signal, not volume. Avoid stale topics
   that {{OWNER_NAME}} has already read; avoid repeating items from
   the prior three newsletters.
3. **Scour the past 7 days** — execute searches; collect candidate
   items (articles, reports, podcasts, regulatory filings, papers,
   notable social posts). Use the provided search tooling
   (`search_fetch` or operator-configured equivalent).
4. **Score for relevance** — each candidate scored against the
   principal's stated interests + goals + IP positions. Items that
   would generate "I already knew that" feedback get cut.
5. **Cluster + draft** — group survivors into themed sections (3-6
   sections is the sweet spot). Each item gets a one-paragraph
   summary, a why-this-matters-to-you line, and a link.
6. **Voice-match** — draft in {{OWNER_NAME}}'s preferred reading
   tone (briefing-style by default; KB derives from the
   voice-attributes corpus).
7. **Hand to CoS** — CoS reviews and either sends or holds. KB never
   sends outbound mail directly.

## Inputs

- The agency vault (Goals.md, Values.md, Work.md, Personal.md,
  Clients.md)
- The IP corpus tags (`interests`, `thought-leadership-areas`,
  `industry-focus`)
- The last 3 weeks of newsletters (for repetition-avoidance)
- An OpenAI-compatible search tool the deployment provides
- The current date (so "past 7 days" is well-defined)

## Outputs

- A draft newsletter written to `profiles/{{KB_ID}}/drafts/
  newsletters/{{YYYY-MM-DD}}.md`
- A kanban card on CoS's lane: "Review weekly newsletter draft
  ({{YYYY-MM-DD}})"
- An entry in `learning_observations` capturing which items
  {{OWNER_NAME}} kept, cut, or asked for more on (feeds future
  curation)

## Supervised learning

Rules tagged `weekly-industry-newsletter`, `general`,
`role:knowledge-base`, `voice:briefing`.

Important learning surfaces:
- **Topic relevance** — {{OWNER_NAME}}'s feedback "I don't care
  about this anymore" cuts the topic from future query plans
- **Source quality** — "low-signal source, drop it" demotes the
  source for future runs
- **Section structure** — "lead with regulatory" or "I read finance
  first" reorders future drafts
- **Voice** — clipped vs. expansive, headline-style vs. essay-style
- **Length** — too long / too short feedback adjusts target word
  count per section

Re-correction trigger: if {{OWNER_NAME}} corrects the same topic /
source / section structure twice within four weeks, escalate — the
learning loop is dropping a rule somewhere upstream.

## Action surface

- (L1 default) — draft the newsletter, hand to CoS for review +
  send
- (L2 — once trust earned) — draft and auto-route to CoS for one-
  click send; CoS confirms in dashboard
- (L3+) — not appropriate for this skill; the principal's brief is
  too personal to fully autonomize

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{KB_ID}}/drafts/newsletters/{{YYYY_MM_DD}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{KB_ID}}/drafts/newsletters/{{YYYY_MM_DD}}.md"
      needle: "## "
  - type: word_count_between
    args:
      path: "{{AGENCY_HOME}}/profiles/{{KB_ID}}/drafts/newsletters/{{YYYY_MM_DD}}.md"
      min: 400
      max: 2000
```

## Failure modes

- **Generic-newsletter trap** — output reads like an aggregated
  industry feed with no principal-specific framing. Mitigation: the
  why-this-matters-to-you line is required for every item; if KB
  can't write one, the item is cut.
- **Repetition** — surfaces items {{OWNER_NAME}} already saw in a
  prior week. Mitigation: the last 3 weeks of newsletter contents
  are part of the input context + dedup pass.
- **Stale focus areas** — {{OWNER_NAME}}'s interests evolved but
  the IP corpus tags didn't. Mitigation: any "I don't care about
  this anymore" correction also flags the corresponding IP tag for
  review.
- **Volume over signal** — too many items, principal stops reading.
  Hard cap: max 12 items, max 6 sections. KB cuts before exceeding.
- **Source monoculture** — every item from the same 2-3 sources.
  Mitigation: diversity check before final assembly; if >40% of
  items share a domain, KB rebalances.

## Self-check

1. Did I read the principal's actual goals/IP this week, or just
   reuse last week's query plan?
2. Is every item paired with a specific why-this-matters-to-you?
3. Did I check the last 3 weeks for repetition?
4. Is the source mix diverse?
5. Did I cut aggressively? (If unsure, cut — the principal's
   attention is the scarce resource.)
6. Is the draft handed to CoS with a kanban card, not sent
   directly?
