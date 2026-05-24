---
skill_id: ip-curator
profile: {{KB_ID}}
role: knowledge-base
autonomy:
  min_level: 1
  action_classes: [draft-only, structural-change]
voice_tags: [precise]
---

# IP curator

Maintains {{ORG_NAME}}'s IP corpus — frameworks, methodology, prior
decisions, established positions, brand voice. Ingests new IP from
CoS-routed inputs; classifies; cross-references; preserves.

## What this skill does

Receive a new IP source (a {{OWNER_NAME}} writing, a framework
document, a transcript). For each:

1. Classify (which area of the corpus does it belong to)
2. Extract canonical claims (the citable units)
3. Cross-reference against existing corpus (deduplication,
   contradiction detection)
4. Store with provenance (source + date + verifier)
5. Update the methodology graph if new relationships emerge

Output is the updated corpus; no work product for clients.

## Inputs

- New IP source (text, file, transcript)
- Provenance (who provided, when, source attribution)
- `domain_hint` (optional) — which area to focus on

## Supervised learning

Rules tagged `ip-curator`, `general`, `role:knowledge-base`. Important:
classification rules (what counts as "framework" vs "methodology" vs
"position"), provenance rules (what counts as a citable source).

## Action surface

- (L1) propose classification + claims; await KB review
- (L4 structural-change) — write to the IP corpus + methodology graph

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{KB_ID}}/context/{{KB_ID}}/ip/{{NEW_DOC_ID}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{KB_ID}}/context/{{KB_ID}}/ip/{{NEW_DOC_ID}}.md"
      needle: "source:"
```

## Failure modes

- **Provenance missing** — claim added without citable source. Hard
  rule: refuses to ingest without source attribution.
- **Contradiction silent** — new claim contradicts existing; ingester
  doesn't notice. Mitigation: cross-reference step always runs,
  escalates contradictions to {{OWNER_NAME}} not auto-resolves.
- **Duplicate sprawl** — same concept ingested multiple times with
  slight wording variations. Dedup by semantic similarity check.

## Self-check

1. Does every new claim cite a source?
2. Did I check for contradictions before writing?
3. Did I check for duplicates before writing?
4. Is the classification consistent with the existing corpus structure?
