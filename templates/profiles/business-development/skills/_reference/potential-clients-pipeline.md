---
skill_id: potential-clients-pipeline
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [direct, warm]
cadence: continuous
trigger: daily-am
---

# Potential-clients pipeline

A continuously-running pipeline manager for {{ORG_NAME}}'s
**potential-clients database** — the bench of prospects who fit the
ICP, aren't yet signed clients, and warrant ongoing cultivation.
This skill does three things daily:

1. **Maintains the bench** — adds new entries from prospect-research
   + referral-scanner; ages out cold ones; promotes warm ones.
2. **Nudges the principal** — surfaces the right 1–3 prospects per
   day to take a small action on, with rough-draft outreach already
   written.
3. **Converts potential → signed** — tracks the pursuit motion per
   prospect; surfaces when a prospect has gone cold and needs a
   different angle.

The whole point is that conversion from potential→signed is rarely
about one perfect pitch; it's about staying *visibly relevant* over
months until the moment is right. This skill is the agency's
patience engine.

## What this skill does

### Pipeline state (`crm.db::leads` with status='potential')

The leads table is the canonical store. This skill uses:
- `status='potential'` — on the bench, never contacted
- `status='active'` — currently in a pursuit motion (first contact
  made; awaiting response or in conversation)
- `status='dormant'` — was active, has gone quiet, needs a
  re-engagement angle
- `metadata` JSON carries: `icp_match_score`, `last_nudge_at`,
  `nudge_count`, `pursuit_motion` (`cold` / `referral` / `event` /
  `content-response` / etc.), `next_action_at`

### Daily run

1. **Ingest new** — read overnight outputs from
   `prospect-research`, `referral-opportunity-scanner`,
   `journalist-relationship`, `podcast-host-relationship`. Insert
   into `leads` with status='potential' if not already there. Tag
   `metadata.source` so attribution is preserved.
2. **Age the bench** — for each `status='potential'` lead:
   re-score against the current ICP hypothesis; demote score by
   small decay each day. If score drops below threshold, mark
   `metadata.archived_reason='ICP_drift'` and move to dormant
   (still queryable; not nudged).
3. **Pick today's nudges** — surface 1–3 prospects warranting an
   action today. Selection logic:
   - Active prospects past their `next_action_at` (highest
     priority — these have an open thread that needs continuing)
   - Potential prospects where a triggering event landed in the
     news (BD news watcher feeds this — "why now" is fresh)
   - Active prospects who've gone quiet ≥30 days (re-engagement
     angle)
   - Potential prospects who've been on the bench longest without
     contact (oldest unstarted pursuit)
4. **Draft the action** — for each surfaced prospect, write the
   actual next message or angle of approach in {{OWNER_NAME}}'s
   voice. Use prior thread context (sent_threads + reply_log) if
   an active pursuit; use ICP + triggering event + prospect
   metadata if first-touch.
5. **Surface to CoS lane** — kanban card "Pipeline nudges —
   {{YYYY-MM-DD}}" with the 1–3 prospects + drafted message +
   one-sentence "why now" each.
6. **Record disposition** — when {{OWNER_NAME}} sends / skips /
   defers, log to `metadata.last_nudge_at` + bump
   `metadata.nudge_count` + reschedule `next_action_at`.

## Inputs

- `_state/crm.db` (leads, contacts, sent_threads, reply_log)
- Recent prospect-research + referral-scan output
- The current ICP hypothesis from the IP corpus
- The news feed / event watchlist
- Sent-thread bodies for context (prior pitches, prior replies)
- The principal's voice corpus

## Outputs

- Updates to `_state/crm.db::leads` (status transitions, metadata
  bumps)
- `profiles/{{BD_ID}}/drafts/pipeline-nudges/{{YYYY_MM_DD}}.md` —
  the daily nudge package
- kanban card on CoS lane: "Pipeline nudges — {{YYYY-MM-DD}}"
- `profiles/{{BD_ID}}/analyses/pipeline-health/{{YYYY-MM-DD}}.md`
  — weekly (Friday) state-of-pipeline summary
- `learning_observation` per outcome (sent / skipped / deferred)

## Per-prospect state

Each potential client carries a per-subject state file under
`_framework/per_subject_state/` keyed by lead id. This holds:
- Prior thread excerpts (most recent 3 exchanges)
- The pursuit-motion narrative ("started cold via Jan article;
  warmed via referral from {client}; went quiet after April")
- {{OWNER_NAME}}'s notes from prior reviews ("don't pitch until
  budget cycle in Sept")
- The current "best angle" hypothesis

This per-subject state is what makes the nudges feel like the
agency *remembers* — not like a CRM auto-reminder.

## Supervised learning

Rules tagged `potential-clients-pipeline`, `general`,
`role:business-development`, `pipeline`, `nudge-cadence`.

Important learning surfaces:
- **Nudge frequency** — "too often" / "I'd have liked another
  nudge on X" tunes per-prospect cadence
- **Aging policy** — "don't drop people from the bench so fast"
  / "stop nudging cold prospects" tunes the decay
- **Angle quality** — corrections to specific drafted angles
  build the angle-craft corpus
- **Pursuit-motion classification** — corrections to how motions
  are labeled
- **Trigger sensitivity** — "this triggering event wasn't actually
  a 'why now'" tightens the trigger filter
- **Voice** — drafted messages that miss {{OWNER_NAME}}'s voice
  get corrections

Re-correction trigger: same prospect / cadence / angle correction
twice in 6 weeks → escalate.

## Action surface

- (L1 default) — surface nudges to CoS lane; {{OWNER_NAME}} sends
  or revises
- (L2 — earned) — for prospects with `pursuit_motion='referral'`
  AND established context, auto-route to CoS for one-click send
- (L3 — earned, narrow scope) — for prospects with `nudge_count=0`
  and triggering event score ≥0.9, auto-route to CoS as
  high-confidence drafts
- (L4+) — never appropriate; first contacts with potential
  clients are too consequential to fully autonomize

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/drafts/pipeline-nudges/{{YYYY_MM_DD}}.md"
  - type: max_items
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/drafts/pipeline-nudges/{{YYYY_MM_DD}}.md"
      heading: "## "
      max: 3
  - type: sql_query
    args:
      db: "{{CRM_DB}}"
      query: "SELECT id FROM leads WHERE status='potential' AND json_extract(metadata,'$.last_nudge_at') IS NOT NULL"
      expect_rows: ">=1"
```

## Failure modes

- **Pipeline bloat** — every news mention gets a new "potential"
  entry; bench grows to thousands; signal drowns. Mitigation:
  ICP-match threshold required before insertion; aging decay
  continuously removes the inert.
- **Nudge spam** — same prospect surfaced 5 days running.
  Hard rule: `last_nudge_at` enforces minimum cooling period
  (default 21 days; pursuit-motion specific overrides exist).
- **Robotic-cadence feel** — nudges fire on calendar, not on
  earned moments. Mitigation: triggering-event-based selection is
  preferred; calendar-based is the fallback when no events fire.
- **Voice substitution** — BD's voice creeps into drafts; the
  agency-to-the-world voice is CoS's. Mitigation: voice profile
  for CoS loaded at draft time; voice-edit pass before surfacing.
- **Privacy / overreach** — drafted message references personal
  data not in the CRM ("saw you posted about your wedding").
  Hard rule: drafts only reference data from CRM metadata +
  public professional sources; nothing from social-personal
  scraping.
- **Lost context** — re-engagement angle ignores prior thread
  history; reads like first-contact. Mitigation: prior thread
  excerpts are required input for any draft on a non-zero
  `nudge_count` prospect.
- **Conversion blindness** — pipeline doesn't notice when a
  prospect signs (`status='converted'` happens elsewhere) and
  keeps nudging. Mitigation: status check before every nudge.

## Self-check

1. Are today's nudges driven by triggering events, not just
   calendar timing?
2. For each nudge, did I load prior thread context if
   `nudge_count > 0`?
3. Does each draft sound like {{OWNER_NAME}}, not me?
4. Am I respecting the 21-day cooling period per prospect?
5. Did I cap surfaced nudges at 3, even if more could plausibly
   fire?
6. Did I check that no surfaced prospect has flipped to
   `status='converted'`?
7. For aged-out prospects, am I archiving with the *reason*, so
   the bench is queryable later if circumstances change?
