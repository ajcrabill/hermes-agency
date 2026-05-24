---
skill_id: thought-leadership-scanner
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise, voice-aware]
cadence: continuous
trigger: daily-am
---

# Thought-leadership opportunity scanner

A continuously-running scanner for thought-leadership opportunities
in {{OWNER_NAME}}'s addressable market — article submissions, letters
to the editor, podcast guest spots, panel invitations, anthology
contributions, and the dozen other shapes thought leadership takes.

**This skill is highly curated, not generic.** Generic thought
leadership is what makes someone forgettable. Real thought leadership
comes from *owning a niche* — being known for one specific corner of
your industry that nobody else owns as completely as you do. This
skill's first job is to help discover {{OWNER_NAME}}'s niche (even
if {{OWNER_NAME}} hasn't named it yet). Its second job is to
constantly hunt for ways to express thought leadership *within* that
niche.

Better to skip a hundred generic opportunities than to squander one
session of {{OWNER_NAME}}'s attention on something that doesn't
deepen the niche.

## What this skill does

### Phase 1 — Niche discovery (runs first; re-runs quarterly)

If `niche.md` doesn't exist yet, or hasn't been reviewed in 90 days:

1. **Pull principal signal** — read Goals.md, Values.md, Work.md,
   Clients.md, the IP corpus, prior writings, transcript archives.
   Walk the patterns: what does {{OWNER_NAME}} return to? What does
   {{OWNER_NAME}} *get angry* about (often a strong niche tell)?
   What does {{OWNER_NAME}} explain repeatedly to clients?
2. **Pull market signal** — search for who else owns this space.
   The niche is where {{OWNER_NAME}}'s repeated focus intersects
   with weak / fragmented existing voice. A crowded space isn't a
   niche; an uncrowded specific intersection is.
3. **Draft niche candidates** — three to five concrete proposals,
   each one sentence. Not "education leadership" — "what trustees
   should do when the superintendent is the problem." Not
   "AI ethics" — "the labor-market consequences of agency-loss in
   coding."
4. **Hand to {{OWNER_NAME}}** — kanban card on CoS lane:
   "Pick the niche (or revise the candidates)". {{OWNER_NAME}}
   selects or rewrites; result lands at `profiles/{{WRITING_ID}}/
   context/{{WRITING_ID}}/niche.md` with a date stamp.

### Phase 2 — Opportunity hunting (runs daily once niche exists)

1. **Build query plans from `niche.md`** — specific search queries
   that index into venues likely to value a contribution on this
   niche. Examples (each niche generates different queries):
   - Industry publications accepting op-eds / contributed pieces
   - Podcasts in adjacent verticals seeking guests
   - Anthologies / collected-essay calls open in the niche space
   - Conference panel openings, especially niche-adjacent
   - Letters-to-the-editor opportunities responding to flawed
     coverage of the niche
   - Substack / publication network cross-posts
   - Industry survey citations / expert-quote opportunities
2. **Score for fit** — every candidate scored on three axes:
   - **Niche-fit** — is this a chance to express the *specific*
     niche, or just adjacent? (Adjacent = cut.)
   - **Audience-fit** — does this venue reach the right readers /
     listeners for the niche?
   - **Effort-to-payoff** — what's the work to produce vs. the
     visibility-yield? (A long-form article in a top-tier venue can
     justify the effort; a guest spot on a 200-listener podcast
     usually can't.)
3. **Cut aggressively** — generic opportunities are *dropped*, not
   surfaced. If a candidate scores below the bar on niche-fit, it
   doesn't appear in the brief at all. Better to surface 1 sharp
   opportunity per week than 8 generic ones.
4. **Brief weekly** — Friday digest to CoS lane: the survivors,
   each with an angle ({{OWNER_NAME}} doesn't have to invent the
   angle), a target outcome, and an effort estimate. For top-1
   opportunities, Writing also drafts a pitch / cover note in
   {{OWNER_NAME}}'s voice.

## Inputs

- The agency vault (Goals.md, Values.md, Work.md, Clients.md)
- The IP corpus (especially `interests`, `thought-leadership-areas`,
  `industry-focus`)
- `profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/niche.md`
  (or absence triggers Phase 1)
- The principal's writing voice corpus (for pitch drafts)
- An operator-configured search tool

## Outputs

- **Phase 1 outputs**: `niche-candidates-{{YYYY-MM-DD}}.md` in
  Writing's draft folder; kanban card on CoS lane
- **Phase 2 outputs**:
  - `profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/opportunity-
    log/{{YYYY-MM-DD}}.md` — full candidate list (including cuts,
    so the principal can spot-check the filter)
  - Weekly brief: `profiles/{{WRITING_ID}}/drafts/opportunity-
    briefs/{{YYYY-MM-DD}}.md` — survivors only, with angles
  - Pitch draft for top-1 opportunity (if any)
  - kanban card on CoS lane

## Supervised learning

Rules tagged `thought-leadership-scanner`, `general`,
`role:writing-support`, `niche-discovery`, `opportunity-scoring`.

Important learning surfaces:
- **Niche specificity** — "this is still too broad" / "this is the
  right level of specific" feedback during Phase 1
- **Cut threshold** — "I would have wanted to see that one" means
  the cut threshold is too aggressive; "stop sending me generic
  ones" means it's too lax
- **Venue quality** — venue feedback ("never pitch X again",
  "always check Y") demotes / promotes sources
- **Angle quality** — Writing's drafted angles get corrected; those
  corrections become the angle-craft corpus for future briefs
- **Voice** — pitch drafts that miss {{OWNER_NAME}}'s voice get
  corrections that flow back to the voice profile

Re-correction trigger: if {{OWNER_NAME}} corrects the same dimension
(niche-fit, cut threshold, venue quality, angle craft) twice within
four weeks, escalate.

## Action surface

- (L1 default) — niche candidates and opportunity briefs surfaced
  to CoS lane; {{OWNER_NAME}} picks
- (L2) — auto-route top-1 opportunity pitch to CoS for review +
  send; CoS confirms
- (L3+) — not appropriate; the principal's public voice is too
  personal to fully autonomize

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/drafts/opportunity-briefs/{{YYYY_MM_DD}}.md"
  - type: file_does_not_contain
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/drafts/opportunity-briefs/{{YYYY_MM_DD}}.md"
      needle: "general thought leadership"
  - type: max_items
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/drafts/opportunity-briefs/{{YYYY_MM_DD}}.md"
      heading: "## "
      max: 5
```

## Failure modes

- **Generic-opportunity creep** — over time, the filter loosens and
  generic opportunities sneak through. Mitigation: weekly cut-rate
  is logged; if cut-rate drops below 70%, Sentinel alerts.
- **Niche drift** — niche.md gets re-written every quarter into
  something different, suggesting it was never the right niche.
  Mitigation: when {{OWNER_NAME}} rewrites the niche, Writing
  surfaces "what changed" — niche evolution is fine; thrashing is
  a signal.
- **Adjacency trap** — opportunities scored as niche-fit when they
  are really just adjacent. Mitigation: the niche-fit scorer has
  to cite the *specific* phrase from niche.md the opportunity
  matches; if it can't, it's adjacent.
- **Voice-substitution in pitches** — Writing's voice creeps into
  pitch drafts. Mitigation: pitches load {{OWNER_NAME}}'s voice
  profile before drafting; pitches get the voice-edit pass before
  surfacing.
- **Quantity-over-quality** — long lists feel productive; they
  aren't. Hard cap: ≤5 survivors in the weekly brief. If more
  survive, raise the bar.

## Self-check

1. Did I read niche.md before scoring opportunities? (If niche.md
   doesn't exist, did I run Phase 1 instead?)
2. For every survivor: can I cite the specific phrase from niche.md
   this matches?
3. Did I cut ≥70% of candidates? (Lower than that, my bar is too
   low.)
4. Is the top-1 pitch in {{OWNER_NAME}}'s voice, not mine?
5. Did I include the cut list so {{OWNER_NAME}} can spot-check?
6. Did I refuse to draft a "thought leadership in general" pitch?
   (The right answer to "we just want your general perspective" is
   to decline and propose a niche-specific angle instead.)
