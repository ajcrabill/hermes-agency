---
skill_id: journalist-relationship
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [direct, warm]
---

# Journalist relationship

Maintains per-journalist state — beat, prior coverage, prior pitches,
follow-up cadence, embargo discipline. Knows when to reach out, when
to wait, when to congratulate (signal-boosting their work).

## What this skill does

Per-journalist record:

- Outlet + beat (e.g. "Education Week, K-12 governance")
- Prior coverage (what they've written about us / our domain)
- Prior pitches (what we sent, what they did with it)
- Cadence preference (how often is too often)
- Embargo rules (any standing arrangements)

Three actions:

1. **Pitch** — draft a pitch when something newsworthy lands
2. **Boost** — when they publish something relevant, draft a thoughtful
   share/comment from {{OWNER_NAME}}
3. **Maintenance** — periodic "still warm?" check on dormant
   relationships

All actions produce drafts for CoS to send.

## Inputs

- Per-journalist state (read from
  `context/business-development/journalists/<id>/`)
- Current event (for pitch or boost)

## Supervised learning

Rules tagged `journalist-relationship`, `general`,
`role:business-development`. Important: embargo discipline rules
(violated once → relationship burned).

## Action surface

- (L1) — draft → CoS
- (L4 structural-change) — update per-journalist state

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/context/{{BD_ID}}/journalists/{{JOURNALIST_ID}}/state.json"
```

## Failure modes

- **Cadence violation** — pitch sent too soon after prior. Self-check
  reads cadence rule.
- **Embargo leak** — material under embargo accidentally surfaces in
  unrelated context. Hard rule: embargoed content tagged + handled
  separately.
- **Beat-confusion** — pitch a K-12 governance journalist on a higher-ed
  story. Match-pitch-to-beat is mandatory.

## Self-check

1. Did I check the cadence rule for this journalist?
2. If embargoed content present: did the embargo check pass?
3. Does the pitch match the journalist's beat?
4. Did I update per-journalist state?
