---
skill_id: crm-sync
profile: {{BD_ID}}
role: business-development
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [direct, precise]
---

# CRM sync

CRM hygiene — keeps the contacts / leads / sent_threads / reply_log
tables accurate. Logs every outbound, matches every reply, updates
lead status from reply sentiment.

## What this skill does

Three modes:

1. **Log outbound** — when CoS sends a draft, log the sent_thread
   linking the gmail thread id to the lead id
2. **Match inbound** — when a reply lands (from `owner-channels-ingress`),
   run the 4-priority matching: thread_id → email → domain →
   unmatched
3. **Update status** — based on reply sentiment (positive / negative
   / neutral / question), update leads.status

Uses `_framework.crm` module for all DB operations.

## Inputs

- Outbound or inbound message + Gmail thread id
- The CRM database

## Supervised learning

Rules tagged `crm-sync`, `general`, `role:business-development`.
Includes sentiment-classification calibration.

## Action surface

- (L1) — propose status updates
- (L4 structural-change) — write to CRM DB

## Verifier criteria

```yaml
verifier:
  - type: sql_query
    args:
      db: "{{BIZDEV_DB}}"
      query: "SELECT * FROM sent_threads WHERE thread_id='{{THREAD_ID}}'"
      expect_min: 1
```

## Failure modes

- **Mismatched reply** — thread id doesn't exist in sent_threads;
  reply gets attributed wrong. 4-priority fallback handles; unmatched
  flagged for owner review.
- **Sentiment miss** — classified positive when reply is actually
  "interested but later." Conservative default: ambiguous → kanban
  task for owner triage.
- **Stale leads** — leads not updated in 90 days. Surfaced by
  weekly-opportunity-scan.

## Self-check

1. Did I run the 4-priority match in order?
2. If unmatched: did I flag it for owner review rather than guess?
3. If status update: did I cite the specific reply text that justified it?
