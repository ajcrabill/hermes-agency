---
skill_id: existing-client-commonality-analyzer
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, precise]
cadence: weekly
trigger: monday-am
---

# Existing-client commonality analyzer

Continuously (weekly cadence) analyzes {{ORG_NAME}}'s signed and
active clients to surface commonalities — the shared dimensions that
made them the right fit. Output is the working hypothesis of
{{ORG_NAME}}'s ideal client profile, which feeds prospect-research
and the referral-opportunity-scanner.

The point isn't to *create* the ICP from scratch — {{OWNER_NAME}}
already has instincts about who the right client is. The point is to
make those instincts measurable, surface ones {{OWNER_NAME}} hasn't
articulated, and catch drift when the active client base diverges
from where {{OWNER_NAME}} thinks they are.

## What this skill does

Once per week (Monday AM):

1. **Pull the active client roster** — from `_state/crm.db::leads`
   where `status IN ('active', 'doc-provided', 'converted')`. Join
   to contacts. Pull each lead's `metadata` JSON for domain-specific
   fields the deployment added.
2. **Pull supporting context** — Clients.md from the agency vault
   (operator's written take on each client); recent reply-log
   activity (who's engaged vs. dormant); won-deal notes if the
   deployment maintains them.
3. **Cluster on commonalities** — examine each of these dimensions
   for shared patterns:
   - Organizational shape (size, structure, lifecycle stage)
   - Industry / sub-industry
   - Geographic concentration
   - The problem that brought them in (the trigger)
   - The buyer persona (role, seniority, decision authority)
   - Engagement style (formal RFP / referral / cold pitch / event)
   - Price point + project shape (one-off / retainer / phased)
   - Pre-existing IP exposure (had read book, heard podcast, etc.)
   - Pre-existing relationship pathway (who introduced them)
4. **Score patterns** — for each candidate commonality, compute:
   coverage (% of active clients sharing it), strength (how
   distinctive among the broader prospect universe), and
   *retention-correlation* (do clients sharing this trait stay
   longer / expand more?).
5. **Compare to last week's analysis** — note drift: are we
   acquiring clients who match the historic pattern, or have we
   drifted? Drift isn't bad — it's a question worth asking.
6. **Surface to {{OWNER_NAME}}** — Monday morning kanban card on
   CoS lane with: top 5 strong commonalities, top 2 emergent
   commonalities (showing up in last 90 days but not historic),
   top 1 drift signal (something we used to share but now don't).
   Each finding cites the specific clients it's drawn from.
7. **Write to IP corpus** — the working ICP hypothesis lands at
   `profiles/{{KB_ID}}/context/{{KB_ID}}/ip/icp-{{YYYY_MM_DD}}.md`,
   tagged for prospect-research + referral-scanner to pull from.

## Inputs

- `_state/crm.db` (leads, contacts, sent_threads, reply_log)
- Clients.md from the agency vault
- The IP corpus (prior ICP iterations for trend analysis)
- Last week's commonality report (for drift detection)

## Outputs

- `profiles/{{BD_ID}}/analyses/icp/{{YYYY_MM_DD}}.md` —
  full analysis with commonality scores
- IP corpus entry: `profiles/{{KB_ID}}/context/{{KB_ID}}/ip/icp-
  {{YYYY_MM_DD}}.md` (the operator-facing summary, KB-curated)
- kanban card on CoS lane: "Weekly ICP brief — review"
- A `learning_observation` capturing which commonalities
  {{OWNER_NAME}} confirmed vs. dismissed (feeds future scoring)

## Supervised learning

Rules tagged `existing-client-commonality-analyzer`, `general`,
`role:business-development`, `icp`.

Important learning surfaces:
- **Dimension weighting** — "stop emphasizing geography; it's
  coincidence" demotes a dimension; "you keep missing the trigger
  pattern" emphasizes one
- **Pattern thresholds** — "5 of 12 isn't a pattern" raises the
  coverage threshold; "I see it at 3 of 12 but you don't surface
  it" lowers it
- **Drift sensitivity** — "stop alarming on drift, it's how we
  grow" reduces drift-flagging; "you missed this drift" sharpens it
- **Clustering** — corrections to how clients group ("X and Y are
  not the same kind of client even though they share Z")

Re-correction trigger: same dimension / threshold / drift correction
twice in 6 weeks → escalate. The ICP framework itself is leaking
upstream.

## Action surface

- (L1 default) — surface analysis to CoS lane; {{OWNER_NAME}}
  reviews + confirms
- (L2 — earned) — auto-publish the IP corpus entry without
  pre-review when commonalities haven't shifted from prior week
- (L3+) — not appropriate; ICP is principal-level strategy

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/analyses/icp/{{YYYY_MM_DD}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/analyses/icp/{{YYYY_MM_DD}}.md"
      needle: "## Strong commonalities"
  - type: sql_query
    args:
      db: "{{CRM_DB}}"
      query: "SELECT COUNT(*) FROM leads WHERE status IN ('active','doc-provided','converted')"
      expect_rows: 1
      min_value: 3   # need at least 3 active clients to do meaningful analysis
```

## Failure modes

- **Spurious correlations** — small N produces "all 3 of our active
  clients are in the same time zone, must matter." Hard rule:
  pattern requires ≥40% coverage AND ≥3 clients to surface.
- **Recency bias** — over-weights the most recent client signed.
  Mitigation: time-decay applied but capped (oldest active client
  still carries ≥30% weight).
- **Surface-vs-substance** — clusters on org name length, brand
  color, etc. Mitigation: dimensions are explicitly enumerated
  above; ad-hoc dimensions need {{OWNER_NAME}} confirmation before
  scoring.
- **Privacy leak** — analysis cites specific clients by name in
  IP-corpus entry. Hard rule: client-naming in the IP entry only
  with operator opt-in; otherwise aggregate-only ("4 of 7 active
  clients").
- **Drift-as-failure** — flags drift as a problem when {{ORG_NAME}}
  is intentionally expanding. Mitigation: drift is *surfaced*, not
  alarmed; {{OWNER_NAME}} decides whether it's a problem.

## Self-check

1. Did I include all active clients, or just the easy-to-categorize
   ones?
2. Does every surfaced commonality meet the coverage + strength
   threshold?
3. Did I check against last week for drift?
4. Is the IP-corpus entry aggregate-only (or operator-confirmed for
   naming)?
5. Did I surface emergent patterns ({{OWNER_NAME}} may not have
   noticed) in addition to historic ones ({{OWNER_NAME}} already
   knows)?
6. Did I avoid spurious-correlation traps?
