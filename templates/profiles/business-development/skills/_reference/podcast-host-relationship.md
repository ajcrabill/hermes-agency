---
skill_id: podcast-host-relationship
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [direct, warm]
---

# Podcast host relationship

Same shape as `journalist-relationship` but for podcast booking. Per-
host state: audience, topic focus, prior episodes, prior pitches,
booking lead time.

## What this skill does

Per-host record:

- Show + audience demographics
- Topic focus + recent guest list
- Prior pitches (what we sent, what they did with it)
- Booking lead time (some are weeks out, some are months)
- Production notes ({{OWNER_NAME}}'s prior episodes — what worked)

Actions:

1. **Pitch** — draft a guest pitch when alignment fits
2. **Follow-up** — manage the booking-to-recording-to-promotion arc
3. **Promotion** — when an episode airs, draft cross-promotion
   content

## Inputs

- Per-host state (`context/business-development/podcasts/<id>/`)
- Current pitch opportunity

## Supervised learning

Rules tagged `podcast-host-relationship`, `general`,
`role:business-development`. Including audience-alignment rules.

## Action surface

- (L1) — draft → CoS
- (L4 structural-change) — update per-host state

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{BD_ID}}/context/{{BD_ID}}/podcasts/{{PODCAST_ID}}/state.json"
```

## Failure modes

- **Audience mismatch** — pitch a niche-policy show on a generic
  topic. Audience-alignment check catches.
- **Lead-time miss** — booked an episode for next week when host
  needs 8 weeks notice. State has lead_time; check before pitching.

## Self-check

1. Does the audience fit {{ORG_NAME}}'s mission?
2. Did I check the lead-time requirement?
3. Did I check {{OWNER_NAME}}'s availability via CoS?
4. Did I update per-host state with the pitch + cadence?
