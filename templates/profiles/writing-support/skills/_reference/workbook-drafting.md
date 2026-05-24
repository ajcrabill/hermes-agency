---
skill_id: workbook-drafting
profile: {{WRITING_ID}}
role: writing-support
autonomy:
  min_level: 1
  action_classes: [draft-only]
voice_tags: [precise]
---

# Workbook drafting

Staff-facing instructional content — workbooks that walk a
practitioner through applying {{ORG_NAME}}'s methodology, step by
step. Usability is the test.

## What this skill does

Given a workbook brief:

1. Identify the audience (which kind of staff member uses this?)
2. Identify the outcome (after this workbook, they can do X)
3. Outline — one step per step, no combined steps
4. Draft each step with: instruction + worked example +
   common-mistake callout
5. KB sends back alignment verdict; iterate as needed
6. Deliver as markdown ready for designer (if formatting matters)
   or staff intranet (if not)

Workbooks are for execution, not inspiration. If a workbook reads
beautifully but a new staff member can't pick it up cold and produce
the right output, it failed.

## Inputs

- `topic` + `audience` + `key_message`
- Source methodology from KB

## Supervised learning

Rules tagged `workbook-drafting`, `general`, `role:writing-support`.
Includes "one step per step" rule, examples-over-abstractions rule.

## Action surface

- (L1) — draft → KB for alignment → revisions → CoS for delivery

## Verifier criteria

```yaml
verifier:
  - type: file_exists
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/workbooks/{{WORKBOOK_ID}}.md"
  - type: file_contains
    args:
      path: "{{AGENCY_HOME}}/profiles/{{WRITING_ID}}/context/{{WRITING_ID}}/workbooks/{{WORKBOOK_ID}}.md"
      needle: "## Worked example"
```

## Failure modes

- **Combined steps** — "Step 4: Plan and execute the X." Hard rule:
  one action per step.
- **No worked example** — abstract rule with no concrete instance.
  Verifier checks for the section.
- **Buried prerequisites** — step 5 needs info from a document never
  introduced. Self-check enumerates prereqs upfront.

## Self-check

1. Can a new staff member execute step-by-step without prior context?
2. Is every step a single action?
3. Are worked examples present and concrete?
4. Did KB sign off on alignment?
