# agency-vault

The principal's context layer. These documents are the source of
truth the agency reads to know what to do, what to refuse, and who
to do it for.

| File | What it answers | Sensitivity |
|---|---|---|
| **Goals.md** | What are we optimizing for this year? | Operational |
| **Values.md** | What won't I trade off, even for big wins? | Operational |
| **Personal.md** | What non-work context shapes scheduling + availability? | Sensitive — limited agent access |
| **Work.md** | What does the agency actually offer? | Operational |
| **Clients.md** | Who pays us, who collaborates with us, who's off-limits? | Sensitive — never quoted outbound |

## Who reads what

- **ChiefOfStaff**: all five — needed for every triage decision.
- **KnowledgeBase**: Goals, Values, Work, Clients — needed for IP
  alignment.
- **SystemSentinel**: none (Sentinel reads framework state, not
  principal content).
- **AnalystJudge**: Goals, Values, Work — needed for dossier
  scoring and red-team calibration.
- **BusinessDevelopment**: Goals, Work, Clients — qualification +
  pipeline. Does NOT read Personal.md or Values.md beyond the
  outbound-relevant subset.
- **WritingSupport**: Values, Work — voice calibration. Reads
  Clients.md only when evaluating client-facing content.

The audit rule `agency-vault-access` enforces these access
patterns — agents that try to load a file outside their access list
emit a `vault-access-violation` event.

## Origin

These files start as templates with `{{PLACEHOLDERS}}`. The Tier 3
deep interview (`agency init --tier 3`) generates the first draft
by interviewing the principal and substituting answers into the
template structure.

After generation, the principal edits freely. Re-running the
interview with `--refresh` regenerates from a fresh conversation
without losing prior edits (the prior version is preserved at
`Goals.md.YYYY-MM-DD.bak`).

## Cadence

- **Goals.md**: monthly principal review; quarterly strategic
  revisit.
- **Values.md**: rarely changes; revisit annually or after a
  significant life/work transition.
- **Personal.md**: as life changes — moving, family changes,
  health changes.
- **Work.md**: as the business evolves — new offerings, new
  capabilities, new tools.
- **Clients.md**: continuously — every client engagement adds or
  modifies a row.

## File ownership

The principal owns every file in this directory. Agents read; they
do not edit. The only exception: CoS may append to `Clients.md` to
log new engagements as they start, with the principal reviewing
weekly.
