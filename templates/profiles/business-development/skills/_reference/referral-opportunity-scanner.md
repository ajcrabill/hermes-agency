---
skill_id: referral-opportunity-scanner
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, warm]
cadence: weekly
trigger: tuesday-am
---

# Referral opportunity scanner

Continuously hunts for potential clients that {{ORG_NAME}}'s existing
clients could refer. Referral pursuit is the highest-ROI BD
activity available — a warm intro from a trusted client converts at
multiples of cold outreach. This skill makes it systematic instead
of accidental.

Pairs with `existing-client-commonality-analyzer`: that skill knows
who the right kind of client *looks like*; this skill scans existing
clients' visible networks (public board memberships, conference
co-panelists, co-authored work, social-graph follows, podcast
co-guesting, etc.) for people matching that profile.

## What this skill does

Once per week (Tuesday AM):

1. **Pull the active client roster** — same source as the
   commonality-analyzer (`crm.db::leads` where status active /
   doc-provided / converted).
2. **Pull the current ICP hypothesis** — the most recent
   `icp-{{YYYY_MM_DD}}.md` in the IP corpus.
3. **For each active client, build a "visible network" map** —
   what's publicly knowable about who they know professionally:
   - Co-listed on association/board pages
   - Co-panelists at conferences (past 24 months)
   - Co-authors / co-editors on publications
   - Mutual follows on professional networks (where visible)
   - Quoted-together in trade press
   - Same alumni / leadership-program cohorts
   - Speaker line-ups at events {{ORG_NAME}}'s clients are on
4. **Score each network-member against ICP** — apply the
   commonality patterns; cut anything that doesn't match the
   profile.
5. **Check the CRM** — drop anyone already in `leads`. Drop anyone
   in `contacts` who's a current client or prior conversation.
6. **Score the referral ask itself** — for each survivor, evaluate:
   - **Strength of the connecting client's relationship** with
     {{ORG_NAME}} (active engagement, warm advocate, dormant?)
   - **Recency** of their visible connection to the target (still
     connected today, or historical?)
   - **Ask shape** — what specifically would {{ORG_NAME}} ask the
     client to do? (forward a 2-line note? make a warm intro? CC
     on a "you should two should talk" email?)
7. **Cut aggressively** — surface only referral opportunities
   where the ask is light, the connection is strong, and the
   target is clearly a fit. Better one perfect referral ask per
   week than five mediocre ones.
8. **Draft the ask** — for top-3 survivors, draft the actual
   message {{OWNER_NAME}} would send to the connecting client.
   Light, specific, easy to say yes to ("would you mind forwarding
   this to X?" + a ready-to-forward note attached).
9. **Surface to {{OWNER_NAME}}** — Tuesday kanban card on CoS lane
   with the top 3 referral opportunities, each with: target,
   connecting client, evidence of connection, suggested ask, and
   a draft message.

## Inputs

- `_state/crm.db` (leads, contacts, sent_threads)
- The most recent ICP hypothesis in the IP corpus
- An operator-configured public-data search tool
- The principal's voice corpus (for ask drafts)
- A "do-not-approach" list (kept by {{OWNER_NAME}} for clients
  who've signalled "please don't ever ask me for intros")

## Outputs

- `profiles/{{BD_ID}}/analyses/referrals/{{YYYY_MM_DD}}.md` —
  full scan including cuts
- Three draft messages: `profiles/{{BD_ID}}/drafts/referral-asks/
  {{YYYY_MM_DD}}-{client-id}.md`
- kanban card on CoS lane: "Weekly referral asks — review"
- A `learning_observation` row capturing which referral patterns
  {{OWNER_NAME}} pursued vs. cut

## Supervised learning

Rules tagged `referral-opportunity-scanner`, `general`,
`role:business-development`, `referrals`.

Important learning surfaces:
- **Client-relationship sensitivity** — "never ask X for intros,
  she's a thoughtful introvert" adds permanent skip; "Y loves
  making intros, ask more often" raises Y's rate
- **Ask-shape preferences** — "I prefer the forward-this approach
  over the cc-me approach" tunes draft shape
- **Network-source quality** — "stop using LinkedIn co-follows;
  they're meaningless" demotes a network source
- **Target-fit calibration** — "this person isn't an ICP match
  even though they tick the boxes" sharpens the scoring
- **Voice** — ask drafts that don't sound like {{OWNER_NAME}} get
  corrections that flow to the voice profile

Re-correction trigger: same client / network-source / ask-shape
correction twice in 6 weeks → escalate.

## Action surface

- (L1 default) — surface referral asks to CoS lane; {{OWNER_NAME}}
  picks and sends
- (L2 — earned) — auto-route top-1 ask to CoS for one-click send
  when the connecting client is in the "comfortable making intros"
  tier
- (L3+) — not appropriate; warm-intro asks are too relational to
  fully autonomize

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/analyses/referrals/{{YYYY_MM_DD}}.md"
  - type: max_items
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/analyses/referrals/{{YYYY_MM_DD}}.md"
      heading: "### Top"
      max: 3
  - type: do_not_approach_check
    args:
      list: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/do-not-approach.md"
      drafts_dir: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/drafts/referral-asks/"
```

## Failure modes

- **Cold approach masquerading as referral** — connecting client
  barely knows the target; the "warm intro" wouldn't actually be
  warm. Mitigation: connection-strength scoring required ≥0.7;
  weak connections cut.
- **Over-asking a single advocate** — same client asked for
  multiple intros per quarter. Hard rule: max 1 ask per client per
  quarter unless {{OWNER_NAME}} explicitly overrides.
- **Stale connections** — connection looks current but is years
  old. Mitigation: recency check on the public-data evidence
  (≤24 months).
- **Privacy leak** — public-data scraping crosses into personal
  rather than professional info. Hard rule: professional-public
  sources only (board pages, conference programs, trade press);
  no social-personal data ever.
- **CRM-duplicate slip** — target already in CRM but matched on
  fuzzy name. Verifier checks normalized email + name pairs.
- **Burning advocates** — asking clients who would say yes out of
  politeness but resent it. Mitigation: the do-not-approach list
  is honored unconditionally; {{OWNER_NAME}}'s "thoughtful
  introvert" judgment is a permanent skip.

## Self-check

1. For each surfaced opportunity, is the connecting-client
   relationship genuinely warm and recent?
2. Has any client been asked for an intro in the last 90 days?
   (If so, skip them this week.)
3. Does the target meet the current ICP, or am I stretching?
4. Is the suggested ask light enough to easily say yes to?
5. Does the draft message sound like {{OWNER_NAME}}, not me?
6. Did I check the do-not-approach list?
7. Am I cutting aggressively, or surfacing volume?
