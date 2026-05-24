# Changelog

All notable changes to HermesAgency are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Major bumps signal breaking deployment changes (manifest schema, on-disk
layout). Minor bumps signal new starter skills, new audit rules, or new
roles. Patch bumps are fixes only.

## [0.22.12-spec] — 2026-05-24

**Spec revision: §13.7 v0.23 plan now Thread A+B+C.** The cross-doc
audit identified eight StrategicPlanning.md commitments the
original Threads A+B didn't cover. v0.22.12-spec adds Thread C
with all eight as explicit v0.23 deliverables, plus matching
acceptance criteria.

Spec-only revision; does not advance the 9th-version milestone
counter.

### Added — `§13.7 v0.23 Thread C` (8 new requirements)

1. **Alignment math thresholds wired into the audit** (≥0.6
   Interim↔Outcome, ≥0.5 Initiative↔Interim, or
   leading-indicator argument when historical data is missing).
2. **8th-grade conversation register + silent SMART math
   translation** — the LLM-driven interview's *how*. Prompt
   loads StrategicPlanning.md §3 + §7.1 as context; system
   message instructs CoS on language register and the
   widget-translation pattern.
3. **Ongoing-refinement loop with layer-1 approval gating** —
   `goals-revision-proposal` skill that proposes Goals/Guardrails
   refinements + files them as kanban tasks for Principal
   approval. Post-setup, the strategic plan isn't frozen.
4. **Audit findings-only semantics** — all six new audit rules
   produce findings, never mutations. Verified by a test that
   asserts no vault filesystem writes during audit runs.
5. **SKILL.md `status:` color taxonomy semantics** —
   Blue/Green/Yellow/Red/Gray with explicit meanings. The
   `stale-skill-status` rule also flags Red/Yellow that has
   persisted 4+ weeks unchanged (strategic plans pivot).
6. **Quarterly top-tier strategic-review mechanism** — new
   `strategic-review-prep` CoS skill fires once per quarter,
   assembles the data, produces a review packet for the
   Principal. The review is Principal-driven; the skill just
   produces the data.
7. **Explicit non-business Outcome prompt** — the interview
   MUST ask the well-rounded-lives question after the
   business-vision question.
8. **Guardrails-side interview prompt content** — the GUARDRAILS
   step's specific questions and follow-ups, part of the
   StrategicPlanning.md §3 context the interview loads.

### Added — eight matching acceptance criteria

Each new thread item has a corresponding acceptance test added
to the v0.23 release gate (lines after the Thread C list).

### Spec header

Bumped v0.22.11-spec → v0.22.12-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

**Next step:** start v0.23 code work. The spec is now complete;
the implementation can target it directly.

## [0.22.11-spec] — 2026-05-24

**Spec revision: cleanup pass after the v0.22.1–v0.22.10 sweep.**
An audit found six internal inconsistencies left behind by the
rapid spec evolution. This release fixes them. No code changes
yet — the v0.23 code work begins next.

### Fixed — `Values.md` references that should be `Guardrails.md`

The v0.22.4-spec aim-vs-brake split renamed Values.md →
Guardrails.md and stopped including Guardrails in the
always-loaded prompt context, but three sentences in the spec
still listed Values.md as always-loaded:

- §1 promise (line 217): updated to name Guardrails.md as
  enforcement-layer-only and Personal/Work/Clients/SOUL as the
  always-loaded background.
- §2.2 spine paragraph (line 715-717): explicitly states the
  aim docs vs Guardrails distinction.
- §8.2 deployment layout vault description (line 1630): "Goals.md
  / Values.md" → "Goals.md / Guardrails.md."

### Fixed — broken StrategicPlanning.md section cross-references

The v0.22.2-spec inserted a new §3 ("Quality criteria") in
StrategicPlanning.md, which renumbered §3-§10 → §4-§11. The
spec's cross-refs to that doc were not updated then:

- §1.1 + §1.7 row 1 + §1.7 testability paragraph: "StrategicPlanning.md
  §5" → "§6" (Three nested testability layers is §6, not §5).
- §13.7 v0.23 plan (line 2291): "StrategicPlanning.md §6.4" →
  "§7.4" (Weekly testability cadence moved from §6.4 to §7.4).

### Fixed — Owner residues that v0.22.7-spec missed

The v0.22.7-spec standardization sweep left ~6 instances of
"Owner" in the live spec body:

- §2.3 section title + body: "Owner-agency interface model" →
  "Principal-agency interface model" (3 spots: title, content,
  and "Owner-action" subhead)
- §3.5 capture flow (SystemSentinel example): "Owner corrected
  the same thing twice" → "Principal corrected the same thing
  twice"
- §7.1 ChiefOfStaffAgent role: "Owner's single conversational
  surface" → "Principal's single conversational surface"
- §13.1: "Owner content migration" → "Principal content migration"

§16 historical change-log entries still reference these section
names as they were originally written — preserved verbatim per
the established historical-record precedent (so e.g. the v0.1.0-spec.1
entry at line 2547 still reads "§2.3 'Owner-agency interface
model'" even though §2.3 itself is now renamed in the live spec).

### Added — `operator` term to the §0 standard-terminology table

New row clarifies the distinction between **operator** (the
human installing / administering the deployment — filesystem
paths, deployment.yaml, install scripts, `agency` CLI on the
shell) and **Principal** (the human the agency serves —
strategic planning, day-to-day work, conversation with CoS).
In a one-person small business, operator IS Principal; in larger
deployments they may be different humans.

### Fixed — stale `~/.agency/` path in `hooks.py:204`

The send-guard error message read *"Edit
`~/.agency/email-access.md`..."* — should be
`~/.hermes/agency-state/email-access.md` per the v0.20 state-collapse.
Updated.

### Spec header

Bumped v0.22.10-spec → v0.22.11-spec.

### Tests

- 242 passing.
- `agency audit --self`: clean.

## [0.22.10-spec] — 2026-05-24

**Spec revision: drop "AI" terminology — biological vs.
technological intelligences.** HermesAgency doesn't use "AI" for
the technological intelligences. The phrase "AI assistant," "AI
tool," "AI chief-of-staff" carries too much consumer-grade
baggage and obscures the framework's point that the agents are
**team members**, not "AI tools."

Standard terms (extended in spec §0):

- **Team members** — generic; includes both biological and
  technological intelligences. Default referent when the
  distinction doesn't matter.
- **Biological intelligences** (or **humans**, when expressly
  relevant) — the Principal is one; any human collaborators are
  others.
- **Technological intelligences** (or **agents**, when expressly
  relevant) — the CoS, BD, KB, Writing, Finance, AnalystJudge,
  Sentinel, etc.
- ⚠️ **NOT used**: "AI" / "artificial intelligence."

Spec-only revision; does not advance the 9th-version milestone
counter.

### Changed — spec §0 "Standard terminology" table

Three new rows added codifying team members / biological
intelligences / technological intelligences, plus an explicit
"NOT used: AI" row with the architectural reasoning.

### Changed — narrative sweep across all three live docs

- **Author byline** (spec §0 header, README, StrategicPlanning.md
  About): "AI Developer for Good Ancestor" →
  "Technological Intelligence Developer for Good Ancestor"
- **Lineage description**: "personal AI chief-of-staff project"
  → "personal chief-of-staff project" (the chief-of-staff
  context already implies the technological-intelligence form)
- **Spec §1 intro line 16**: "doesn't want to re-teach their AI
  ten times" → "doesn't want to re-teach their agents ten times"
- **Spec §1.2 differentiator**: 'Most "AI assistant" tools forget
  context...' → "Most consumer-grade technological-intelligence
  tools forget context..."
- **Spec §1.6 + README big-tech contrast**: "AI assistants,
  multi-agent workflows, persistent memory..." →
  "technological-intelligence assistants, multi-agent workflows,
  persistent memory..."
- **Spec §1.7 + README competitive thesis**: "the small business
  that masters their own AI agency wins" → "the small business
  that masters their own agency wins" (the "AI" qualifier was
  redundant — HermesAgency already establishes "the agency" as
  the standardized term)
- **StrategicPlanning.md §6.4** + **§11 summary**: same
  consumer-grade-tool / technological-intelligence-assistant
  swaps

### Preserved — §16 historical change-log entries

Line 3028 in §16 still reads "(AI assistants, multi-agent
workflows...)" — preserved verbatim per the precedent that §16
describes what past spec text said, not what current spec text
should say.

### Spec header

Bumped v0.22.9-spec → v0.22.10-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.9-spec] — 2026-05-24

**Spec revision: Outcomes can be non-business — well-rounded
lives are a strategic priority.** Goals aren't limited to business
matters. The CoS actively encourages the Principal to include at
least one non-business Outcome — health, family, marriage,
friendships, hobbies, faith, community, learning, whatever matters
to them as a whole person. The agency supports those Outcomes
with the same SMART discipline + Interim Goals + Initiative
mappings as business Outcomes.

The framework-level commitment: **at HermesAgency, we believe all
of our team members — biological and technological — deserve
well-rounded lives.** The interview, the worked example, and the
public README all reflect that.

Spec-only revision; does not advance the 9th-version milestone
counter.

### Changed — `docs/StrategicPlanning.md` §1.1 Outcomes

New paragraph after the intro: "Outcomes are not limited to
business matters. HermesAgency is built on the belief that all
of its team members — biological and technological — deserve
well-rounded lives. The CoS actively encourages the Principal to
include at least one non-business Outcome..." Both example forms
shown: a business Outcome (coaching revenue) and a personal one
(weekly exercise hours).

Updated bullet text: "Reflect a result the Principal cares
about" (was "business result"). Last bullet adds: "The CoS
encourages at least one Outcome to come from outside the
business — a well-rounded life is itself a strategic priority."

### Changed — `docs/StrategicPlanning.md` §3.1 Outcome quality criteria

First bullet broadened: "Reflect a result the Principal cares
about, not inputs or outputs." Examples now show both business
("Revenue from coaching engagements") and personal ("weekly
hours of focused exercise"). Adds explicit note:
"**Outcomes can be business OR personal** — the CoS actively
encourages at least one non-business Outcome per the §1.1
well-rounded-lives commitment."

### Changed — `docs/StrategicPlanning.md` §3.5 step 1

"Listen for vision" expanded to include the non-business prompt.
After the business-vision question, the CoS asks:

> *"At HermesAgency, we believe all of our team members deserve
> well-rounded lives. Is there something outside the business —
> your health, your family, your marriage, a hobby, your faith —
> that you'd like the agency to support you on? You don't have
> to name one if it doesn't feel right, but we'd encourage it."*

If the Principal names one, the CoS treats it as an Outcome of
equal standing and runs the same SMART translation.

### Added — `docs/StrategicPlanning.md` §8 worked example

New **Outcome 3 — Personal health (the non-business Outcome)**:
*"Weekly hours of focused exercise will increase from 1 hour in
January 2026 to 4 hours by December 2027."* Plus a supporting
Interim Goal (calendar protection for exercise blocks) and two
Initiatives (`cos/exercise-block-protector.py` deterministic,
`cos/weekly-exercise-checkin` agentic) showing how the same
strategic structure applies to a personal Outcome.

### Changed — `README.md`

Strategic-planning paragraph closes with: "**Goals don't have to
be business-only**: HermesAgency is built on the belief that all
of our team members — biological and technological — deserve
well-rounded lives, so the CoS actively encourages the Principal
to include at least one non-business Outcome (health, family,
marriage, hobbies, faith, whatever matters)."

### Spec header

Bumped v0.22.8-spec → v0.22.9-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.8-spec] — 2026-05-24

**Spec revision: the Principal's privilege + 12-60 month Outcome
horizon + widget-translation example.** Three closely related
clarifications:

1. **The Principal's privilege.** §3.5 now explicitly states that
   the agency takes everything it can off the Principal's plate
   within the parameters (Guardrails, autonomy gates, send-guard,
   etc.) **until the Principal chooses otherwise.** The Principal
   can take over any aspect of any layer at any time, for any
   reason, without explanation. That asymmetry — agency always
   proposing to do more, Principal always free to do less by
   reclaiming — is the right design tension. The CoS adjusts when
   the Principal leans in.

2. **Outcome horizon: 12-60 months** (minimum 12, maximum 60).
   Previously the doc said 1-3 years; updated to 1-5 years per
   AJ's clarification. Most small-business Outcomes still land in
   the 24-36 month range, but the framework formally allows up to
   60 months.

3. **Widget-translation example.** §3.5 step 3 now shows the
   silent translation work the CoS does. Principal casually says
   *"I want to be selling three widgets a month."* CoS does the
   math behind the scenes (3 widgets/month × 36 months = 108
   widgets cumulative over three years) and proposes back: *"How
   about we aim for selling 0 widgets in January 2026 growing to
   108 widgets by January 2029?"* The Principal never has to know
   the words "cumulative" or "SMART"; they just nod at the version
   that feels right.

Spec-only revision; does not advance the 9th-version milestone
counter.

### Changed — `docs/StrategicPlanning.md`

- **§1 three-layer model diagram** — "1-3yr" → "12-60mo" at the
  Outcome layer.
- **§1.1 Outcomes section** — duration bullet updated: "Lasts
  12-60 months (minimum 12, maximum 60; most land 24-36)."
  Intro: "what success looks like for the business in 1-5 years."
- **§3.1 Outcome quality criteria** — "Span 1-3 years" bullet
  rewritten with explicit minimum/maximum: "Span 12-60 months
  (1-5 years). The **minimum** distance between starting date
  and ending date is 12 months; the **maximum** is 60 months."
- **§3.2 Guardrails** — stability horizon updated: "stable across
  the same horizon as the Outcomes (12-60 months)."
- **§3.5 Division of responsibility** — table column header
  "Owner's role" → "Principal's role" (fixes terminology leftover
  from v0.22.7). Layer-2 / layer-3 cells now read "doesn't appear
  in their conversation, *unless they choose to lean in*."
- **§3.5 new paragraph** — codifies the Principal's privilege and
  the default operating posture explicitly.
- **§3.5 step 1** — interview prompt: "Looking ahead one to five
  years" (was "a year or two").
- **§3.5 step 3** — widget-translation example added showing the
  CoS's silent SMART math.
- **§3.5 step 5 heading** — "Owner revises and approves" →
  "Principal revises and approves."
- **§7.1 authorship table** — "Approved by: **Owner**" →
  "Approved by: **Principal**."
- **§7.1 structure diagram** — "1-3yr" → "12-60mo" for all
  Outcomes.

### Changed — `docs/HERMES_AGENCY_SPEC.md`

- §1.1 Layer-1 Outcome description: "1-3 year horizon" → "12-60
  month horizon."

### Changed — `templates/agency-vault/Goals.md.template`

- Outcomes section description: "1-3 year horizon" → "12-60
  month horizon (minimum 12, maximum 60)."

### Spec header

Bumped v0.22.7-spec → v0.22.8-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.7-spec] — 2026-05-24

**Spec revision: standardized terminology — Principal, small
business, agency, CoS.** Across the docs, the human who
interfaces with HermesAgency had been called many things —
"owner," "small-business owner," "business owner," "solopreneur,"
"business leader." Standardized on **Principal** (capitalized).
The entity HermesAgency is designed for is consistently **small
business** (lowercase). The collection of all agents is **the
agency**. The specific agent that owns strategic planning is
**the CoS** (Chief of Staff).

Spec-only revision; does not advance the 9th-version milestone
counter. Code-side renames (yaml field names, skill names,
template placeholders, setup-interview prompts) ship as part of
v0.23.

### Added — spec §0 "Standard terminology" subsection

New reference table in the §0 lineage section codifying the
standard terms and noting which contexts retain older terminology:
§16 historical change-log entries (preserved verbatim as historical
record) and code references (yaml `owner:` field, skill
`owner-channels-ingress`, etc.) where the rename ships in v0.23.

### Changed — `docs/StrategicPlanning.md`

Sweep through the doc. ~80 instances of "the owner" / "owner's" /
"small-business owner" / "business owner" / "solopreneur" replaced
with the standard terms. Anti-pattern examples in §3.3 left as
fragments (those are intentionally illustrating bad forms).

Specific clarifications:
- §1.3 test #2 "One owner" → "One agent profile" — the agent
  ownership concept gets a distinct phrase, separate from the
  Principal concept
- §1.3 test #6 "Owner has authority" → "Agent profile has
  authority" — same distinction
- §5 Playbook page table: "Owner" field → "Agent profile
  (responsible)" — preserves the `owner_profile` frontmatter key
  but in prose uses the disambiguated phrase
- §8 worked example: "Owner profile: Devon (BD)" → "Agent
  profile: Devon (BD)"
- §9 "What if I'm a solopreneur" question → "What if my small
  business is just me"

### Changed — `docs/HERMES_AGENCY_SPEC.md`

Sweep through the live spec body (§0 through §13.7). ~75
"owner" / "owner's" / "small-business owner" / "small-agency
owner" instances replaced. §16 historical change-log entries
preserved verbatim. Code references (`owner:` yaml field,
`owner-channels-ingress` skill name, SQL column comments referring
to literal 'owner' values stored in DB) retained until v0.23
ships the corresponding code-rename work.

Key replacements:
- §1 intro: "designed for and by small-business owners" →
  "designed for small businesses — for and by Principals who
  run them"
- §1.1 always-loaded context paragraph: "the Principal's
  declared goals" everywhere (consistent throughout)
- §1.4 promise: "every correction the Principal gives"
- §2.0 — §2.2 architecture text: "the Principal" throughout
- §13.7 v0.23 plan: aligned with the new terminology

### Changed — `README.md`

Intro paragraph: "Designed for small businesses — for and by
Principals who run them." System-1 description: "the
Principal's declared goals" / "the Principal's declared values."
"Win new business" lead-in: "The Principal of a small business
wears every hat." Profile descriptions: "the one face to the
Principal."

### Code work deferred to v0.23

The following code-level renames will ship in v0.23 along with
the other interview-restructure work:

- `_framework/constants.py` — any `OWNER_*` constants → `PRINCIPAL_*`
- `templates/agency-vault/*.template` — `{{OWNER_NAME}}` →
  `{{PRINCIPAL_NAME}}`
- `hermes_agency_plugin/setup/interview.py` — OWNER step renamed
  to PRINCIPAL step
- `deployment.yaml` schema — `owner:` field renamed (with
  backward-compat read)
- Skill name `owner-channels-ingress` → `principal-channels-ingress`
- SQL schema column comments / actor enum values that store
  'owner' as a literal value
- Tests touching any of the above

### Spec header

Bumped v0.22.6-spec → v0.22.7-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.6-spec] — 2026-05-24

**Spec revision: strategic-planning is the CoS's job, not the
owner's.** Bundles three closely-related changes:

1. **Quality criteria** (§3 of StrategicPlanning.md, added in
   v0.22.5-spec but extended here): a reference section the CoS
   loads during setup interviews.
2. **Precise SMART definition** (per AJ's clarification): each
   letter has a deliberate meaning, with starting/ending date
   (month/year) and starting/ending point required for
   Measurable. Examples throughout the doc cleaned up to
   consistently use month/year (no FY / quarter shorthand) and
   to have full start-point + start-date + end-point + end-date.
3. **The setup-interview UX principle**: the owner doesn't need
   to know the framework terminology, the conversation defaults
   to 8th-grade reading level, and the owner only owns layer 1
   (Outcomes / Guardrails) — Interim Goals, Interim Guardrails,
   and Initiative mappings are all the CoS's behind-the-scenes
   work.

Spec-only revision; does not advance the 9th-version milestone
counter.

### Changed — `docs/StrategicPlanning.md` §3 (Quality criteria)

- **SMART definition rewritten precisely.** The brief 5-line
  version is replaced with AJ's full definition:
  - Specific = narrow focus of action, not trying to do
    everything at once / be all things to all people
  - Measurable = starting date (month/year) + ending date
    (month/year) + starting point + ending point
  - Attainable = ending point accomplishable by ending date
    using time + talent + treasure
  - Results-focused = tied to the larger vision and/or values
    of the business
  - Time-bound = starting date and ending date
- Canonical SMART statement form made explicit: *"<Subject +
  measure> will increase (or decrease) from <starting point> in
  <starting month/year> to <ending point> by <ending month/year>."*
- Note added explaining why month/year (not Q1/FY shorthand):
  quarters and fiscal years vary by business; month/year is
  unambiguous, sortable, makes time-bound testable.

### Changed — `docs/StrategicPlanning.md` §3.5 (How the CoS uses this)

Expanded substantially. The principle is now explicit: **the
owner doesn't need to know any of the framework**. Conversation
defaults to 8th-grade reading level. New division-of-responsibility
table:

- **Owner**: talks about vision (Outcomes) and values (Guardrails);
  reviews + approves layer-1 rough draft.
- **CoS**: translates vision into SMART Outcomes, translates
  values into prohibition Guardrails, drafts Interim Goals,
  Interim Guardrails, and Initiative mappings entirely behind
  the scenes.

Six-step conversation flow specified (listen for vision → listen
for values → translate silently → present rough draft → owner
revises and approves → CoS drafts the rest). The `.configured`
marker is not written until the owner approves the layer-1 draft.

Ongoing revision (post-setup) clarified: three sources — daily
implementation, supervised learning loop, weekly/quarterly
review. **Layer-1 refinements always go back to the owner for
approval; layer-2 and layer-3 refinements are CoS's working
drafts.**

Implementation note added: for v0.23 interview code, the prompt
must have StrategicPlanning.md §3 + §7.1 loaded as context. Same
pattern as skill-load context everywhere else.

### Changed — `docs/StrategicPlanning.md` §7.1 (file structure)

Added authorship table making explicit who writes each layer:

| Layer | Authored by | Approved by |
|---|---|---|
| Outcomes | CoS drafts from owner's vision | **Owner** |
| Guardrails | CoS drafts from owner's values | **Owner** |
| Interim Goals | CoS | CoS (working hypotheses) |
| Interim Guardrails | CoS | CoS (working hypotheses) |
| Initiative refs | CoS proposes mappings | CoS (working hypotheses) |

### Changed — month/year date discipline across examples

Fiscal-year ("FY2025") and quarterly ("Q1 2026") notation
replaced with specific months throughout §8 worked example and
§1.1 / §3.1 inline examples. Examples without proper
start-point + start-date + end-point + end-date got cleaned up:

- `lookalike-prospect-builder`: added "from 0 in February 2026
  to 50 per quarter by June 2026"
- `pipeline-watchdog.py`: added "from 20% in March 2026 to 90%
  by June 2026"
- Interim Guardrail 1.1: added "from 0% in February 2026 to
  100% by March 2026"
- `values-fit-screen-prepper`: added the same start/end framing

Anti-pattern examples (§3.2, §3.3) intentionally left as
fragments — those are illustrating what doesn't work.

### Changed — spec §13.7 v0.23 plan (Thread B)

The `/agency setup` interview bullet expanded with four explicit
requirements:

1. Interview prompt loads `StrategicPlanning.md` §3 + §7.1 as
   context.
2. Conversation defaults to 8th-grade reading level; register
   shifts up only when warranted.
3. Owner is only asked about vision (Outcomes) and values
   (Guardrails) — Interim Goals, Interim Guardrails, and
   Initiative mappings stay behind the scenes.
4. Before `.configured` is written, the CoS presents the
   rough-draft `Goals.md` and `Guardrails.md` (layer 1 only)
   to the owner for revision and approval.

### Spec header

Bumped v0.22.5-spec → v0.22.6-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.5-spec] — 2026-05-24

**Spec revision: Initiatives ARE skills and scripts.** Collapses
the "Initiative" concept into HermesAgency's existing structure:

- **Agentic Initiative = Skill** (LLM-driven, in `SKILL.md`)
- **Deterministic Initiative = Script** (code-driven, in `.py` / `.sh`)

No separate Initiative artifact, no `Initiatives/` subdirectory,
no duplicate Playbook page document. The Initiative's strategic-
planning metadata (Outcome ref, Interim Goal ref, outcome metric,
status, alignment argument, output/input metrics) lives in the
existing SKILL.md frontmatter or script docstring. The strategic
plan's input layer is *literally* the agency's existing catalog
of skills and scripts.

This collapse was implicit in the previous spec revisions
(StrategicPlanning.md §5.3 already said "skills are agentic
initiatives") but the doc still talked about Playbook pages as
separate artifacts and the v0.23 plan still called for an
`Initiatives/` subdirectory. v0.22.5 unifies the framing.

Spec-only revision; does not advance the 9th-version milestone
counter.

### Changed — `docs/StrategicPlanning.md`

- §1.3 (Inputs) renamed "Inputs (Initiatives = Skills + Scripts)";
  explicit table: agentic Initiative = Skill, deterministic
  Initiative = Script. The six tests for "strategic Initiative"
  now read as criteria for what makes a skill/script *strategic*
  (vs. ad-hoc utility work).
- §3 renamed "What makes a skill/script a strategic Initiative."
  Distinguishes strategic skills/scripts (have alignment metadata,
  in the plan) from utility skills/scripts (legitimate but not
  strategic).
- §4 renamed "The Initiative Playbook page — IS the SKILL.md /
  script docstring." Maps the Playbook fields to proposed SKILL.md
  frontmatter keys: `outcome`, `interim_goal`, `outcome_metric`,
  `owner_profile`, `status`, `alignment_argument`, etc.
- §6.1 structure block updated — leaf refs point at `profile/skill`
  or `profile/script.py`, not at `Initiatives/<slug>.md`.
- §6.3 retitled "Skills and scripts ARE the input layer."
- §6.5 audit-rule list updated: `stale-playbook` → `stale-skill-status`
  (since there's no separate Playbook artifact).
- §7 worked example rewritten with real skill/script references
  (e.g., `devon/lookalike-prospect-builder` *(agentic Initiative)*,
  `devon/pipeline-watchdog.py` *(deterministic Initiative)*).
- §8 "Initiative or just a hope?" common question reframed as
  "strategic Initiative or just utility work?"
- §9 "Where this lives" table — `Initiatives/<slug>.md` row
  replaced with rows pointing at the existing
  `profiles/<profile>/skills/<skill>/SKILL.md` and `scripts/<name>.py`
  paths.
- §10 summary updated to name the skill/script = Initiative
  mapping.

### Changed — `Goals.md.template` and `Guardrails.md.template`

Leaf references at the Interim Goal / Interim Guardrail level now
point at `profile/skill` or `profile/script.py` instead of
`Initiatives/<slug>.md`. The header note clarifies that
"Initiatives ARE the agency's skills and scripts."

### Changed — spec §1.1

Layer-3 description updated to explicitly state: "Initiatives ARE
skills and scripts. There's no separate Initiative artifact —
the SKILL.md / script docstring carries the alignment metadata
(Outcome ref, Interim Goal ref, outcome metric, status,
correlation argument) in frontmatter."

### Changed — spec §13.7 v0.23 plan (Thread B)

- Removed: "New vault subdirectory `Initiatives/` holds one
  Playbook page per Initiative."
- Added: "**No new vault subdirectory.** Initiatives ARE skills
  and scripts — they already live under
  `~/.hermes/agency-state/profiles/<profile>/skills/` and
  `.../scripts/`. The strategic-planning metadata goes in the
  existing SKILL.md frontmatter (new optional keys: `outcome`,
  `interim_goal`, `outcome_metric`, `status`, `alignment_argument`,
  `output_metrics`, `input_metrics`) or script docstring."
- Audit rules: `stale-playbook` renamed to `stale-skill-status`.

### Changed — README

"Plan your next quarter" preamble paragraph now mentions: "agentic
Initiatives are skills (LLM-driven, in SKILL.md) and deterministic
Initiatives are scripts (code-driven). The strategic plan's input
layer is *literally* HermesAgency's existing catalog of skills and
scripts."

### Spec header

Bumped v0.22.4-spec → v0.22.5-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.4-spec] — 2026-05-24

**Spec revision: Goals are aim, Guardrails are brake.** Sharpens
the architectural distinction between the two strategic-plan
documents. `Goals.md` is part of the always-loaded background
context (the agency is always *aimed*); `Guardrails.md` is loaded
only by the enforcement layer — Sentinel, AnalystJudge (audit),
and send-guard — so the agency is **aimed by Goals and checked
by Guardrails**, not constrained by Guardrails on every turn.

Putting Guardrails into the always-loaded prompt would bias the
agency toward defensive thinking on every turn (*"how could this
go wrong?"*). A good strategic operator generates work aimed at
the Outcomes, then checks the work against the Guardrails — two
loops, two cadences, two architecturally distinct concerns.

Also: **Values.md → Guardrails.md rename** (design contract;
file/code rename ships in v0.23). The values-as-character-traits
framing wasn't structurally enforceable; values expressed as
Guardrails (prohibitions + SMART Interim Guardrails) are. Each
core value (e.g., "honesty") becomes a Guardrail (e.g., "the
business will not publish content that misrepresents what the
owner knows or believes") with SMART Interim Guardrails (e.g.,
"100% of outbound communications pass a documented honesty
self-check").

Spec-only revision; does not advance the 9th-version milestone
counter.

### Changed — `templates/agency-vault/Guardrails.md.template`

Restructured to absorb the values content. Each core value now
captured as a Guardrail with 1-3 Interim Guardrails underneath.
Explicit "Where Guardrails are loaded" section names Sentinel +
AnalystJudge + send-guard as the loading points; explicit "Where
Guardrails are NOT loaded" notes the always-on context exclusion
and why (avoiding defensive bias on every turn).

### Kept transitionally — `templates/agency-vault/Values.md.template`

Annotated with a transitional banner pointing at `Guardrails.md`
and the v0.23 code-rename schedule. The actual deletion ships in
v0.23 alongside the code rename (constants, setup interview's
VALUES step, v7 migration, skill SKILL.md refs). Until then, both
templates coexist — v0.22 deployments still write Values.md from
the Tier 3 interview; v0.23 will migrate that content into
Guardrails.md and remove Values.md.template.

### Changed — `docs/StrategicPlanning.md`

- §2 (Guardrails section) — added §2.1 "Where Guardrails are
  loaded — *not* always-on context" with the aim/brake table
  (Goals.md → continuous via pre_llm_call; Guardrails.md →
  enforcement-time via Sentinel/AnalystJudge/send-guard) and the
  architectural reasoning (avoiding defensive bias).
- §6.2 (always-loaded context) — renamed to "Always-loaded context
  — Goals only, not Guardrails"; explicit that Guardrails.md is
  deliberately excluded from the always-loaded background.
- Notes the v0.22-spec Values.md → Guardrails.md rename and why.

### Changed — spec §1.1

The always-loaded context list now reads: Goals.md, Personal.md,
Work.md, Clients.md, per-profile SOUL.md. **Guardrails.md is
explicitly NOT in this list.** New paragraph after the loop
explains where Guardrails.md is loaded instead (Sentinel,
AnalystJudge, send-guard) and the pattern: *"the agency
generates work in service of Goals.md; the watchdog layer checks
that work against Guardrails.md."*

### Changed — spec §1.7 systems table

- Row 1 (learning loop): aim-docs list updated; explicit note
  that Guardrails.md is NOT in the always-loaded set.
- Row 4 (Sentinel): notes Sentinel reads Guardrails.md to know
  what to flag. Sentinel is the architectural watchdog; the doc
  is the content, Sentinel is the mechanism.
- Row 6 (send-guard): notes send-guard reads Guardrails.md at
  outbound-mail `pre_tool_call` time.
- Row 7 (audit): re-tagged as "AnalystJudge profile"; notes the
  audit reads Guardrails.md to surface drift.

### Changed — spec §13.7 v0.23.0 plan

Thread A (always-loaded context audit) extended with the
Values.md → Guardrails.md rename and the enforcement-layer wiring
(Sentinel + AnalystJudge + send-guard each reading Guardrails.md).
Migration is additive — existing deployments get Guardrails.md
populated from their Values.md content.

### Changed — README

Intro paragraph: "The owner's declared goals (in `Goals.md` and
the other operational context docs) are always part of the
background... The owner's declared values (in `Guardrails.md`)
are loaded into the enforcement layer — Sentinel, the audit, and
the send-guard — so the agency is **aimed by Goals and checked
by Guardrails**, not constrained by Guardrails on every turn."

System-1 description: same aim/brake framing.

### Spec header

Bumped v0.22.3-spec → v0.22.4-spec.

### Tests

- No code changed; no test churn (242 still passing). The
  Values.md → Guardrails.md *code* rename ships in v0.23 with its
  own test churn.
- `agency audit --self`: clean.

## [0.22.3-spec] — 2026-05-24

**Spec revision: three nested testability layers.** Makes explicit
the precise role of the 7-step learning loop in the strategic-
planning architecture: it's the **input-layer testability
mechanism**, answering *"are we implementing the strategies?"* at
continuous cadence. The weekly strategic-plan health check
answers the mid-tier question *"are we deploying resources
wisely?"* (testing inputs against Interim Goals). The quarterly
strategic review answers the top-tier question *"do we have the
right strategies to get the results the owner wants?"* (testing
Interim Goals against Outcomes). Three layers, three cadences,
one underlying data structure. Spec-only revision; does not
advance the 9th-version milestone counter.

### Added — `docs/StrategicPlanning.md` §5 "Three nested testability layers"

New top-level section between the Initiative Playbook (§4) and
the operationalization (§6). Defines:

- §5.1 — Input-layer testability (the 7-step learning loop)
- §5.2 — Mid-tier testability (weekly health check, inputs against
  Interim Goals)
- §5.3 — Top-tier testability (quarterly review, Interim Goals
  against Outcomes)
- §5.4 — Why nested testability is load-bearing (most "AI
  assistant" tools work at the input layer only; most
  strategic-planning tools work at the outcome layer only;
  HermesAgency connects both through one data structure read at
  three time horizons)

Renumbered the rest of the doc accordingly (former §5 →
"operationalization" → §6; §6 worked example → §7; etc.). The
final-paragraph summary rewritten to surface the three
testability questions.

### Changed — spec §1.1 title and lead paragraph

Section title becomes "**The seven-step learning loop — the
input-layer testability mechanism**." New lead paragraph names
the loop's precise role in the three-layer model and points to
StrategicPlanning.md §5.

### Changed — spec §1.7 systems table

Row 1 updated to flag the supervised learning loop as the
continuous-cadence test in the three-layer testability model.

### Added — spec §1.7 testability paragraph

New paragraph after the seven-systems table explains that the
mid-tier and top-tier testability mechanisms are not additional
reliability systems — they're the same data substrate (rules,
firings, audit findings, alignment correlations) read at three
different time horizons.

### Changed — README

Intro adds a second paragraph naming the three-layer strategic-
planning model and the three testability questions. The
intro paragraph wasn't extended; instead a new paragraph
follows it, calling out: "the daily work and the long-term
direction are structurally connected, not just culturally linked."
Links to `docs/StrategicPlanning.md`.

### Spec header

Bumped v0.22.2-spec → v0.22.3-spec.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.2-spec] — 2026-05-24

**Spec revision: three-layer strategic-planning model.** Adds
`docs/StrategicPlanning.md` (~4,000 words) — a framework document
translating AJ's public-sector strategic-planning practice
(Outcomes → Interim Goals → Initiatives, all SMART, alignment
math not opinion) into HermesAgency's language. Updates the
agency-level templates and the spec to make the three-layer
structure load-bearing across the framework. Pure docs/templates;
no code change yet — implementation lands in v0.23.

### Added — `docs/StrategicPlanning.md`

The companion framework doc to the spec. Defines:

- **Three-layer model**: 1-3 Outcomes (lag, 1-3yr), 1-3 Interim
  Goals per Outcome (mid-cycle, 6-12mo), 1-5 Initiatives per
  Interim Goal (input layer, owned by profiles).
- **Guardrails** as the parallel non-negotiable structure with
  matching Interim Guardrails + Guardrail-aligned Initiatives.
- **Initiative definition** (six tests: SMART, one owner, ≥4hr/wk,
  resources, current→future state, ~80% owner authority).
- **Alignment is math, not opinion** — ≥0.6 correlation between
  Interim Goal and Outcome; ≥0.5 between Initiative and Interim
  Goal. Expect ~95% of candidate Initiatives won't align — that's
  normal; the job is to find and resource the few that do.
- **The Playbook page** — per-Initiative tracking artifact, all
  fields specified (Outcome ref, Interim Goal ref, problem,
  solution, owner, FTE, budget, output metrics, input metrics,
  Blue/Green/Yellow/Red/Gray status).
- **A worked small-business example** (coaching consulting
  practice — not the school-system example from the source doc).
- **Common questions** covering update cadence, plan adoption,
  initiative-or-just-a-hope tests, alignment math, and the
  owner-as-decider + agency-as-proposer collaboration model.

The doc explicitly skips the governance-vs-management distinction
from the public-sector source — not relevant in a one-owner
business. The core alignment discipline and SMART-at-every-layer
requirement are preserved.

### Changed — `templates/agency-vault/Goals.md.template`

Restructured from a flat "annual goals + active projects" list
into the three-layer structure:

```
Outcome 1 (SMART, 1-3yr)
  Interim Goal 1.1 (SMART, 6-12mo)
    Initiative 1.1.a → Initiatives/init-1-1-a.md
    Initiative 1.1.b → Initiatives/init-1-1-b.md
  Interim Goal 1.2
    Initiative 1.2.a
Outcome 2 ...
```

Cross-references `docs/StrategicPlanning.md` and the parallel
`Guardrails.md`.

### Added — `templates/agency-vault/Guardrails.md.template`

New template for the parallel non-negotiables structure. Distinct
from `Values.md` (which is philosophy): `Guardrails.md` is the
**SMART, structural consequence** — the lines that don't get
crossed, expressed in a form the agency can enforce. Same
three-layer structure (Guardrail → Interim Guardrails → Initiative
refs).

### Changed — spec §1.1 (the seven-step learning loop)

The "always-loaded context" paragraph expanded to name
`Guardrails.md` alongside `Goals.md`, and to spell out the
three-layer structure that the strategic-planning doc defines.
The 7 steps themselves are unchanged.

### Changed — spec §13.7 v0.23.0 entry

Expanded from "always-loaded agency-context audit" alone to two
threads:

- *Thread A* — the always-loaded context audit (unchanged from
  the v0.22.1-spec scope).
- *Thread B* (new) — the three-layer strategic-planning structure:
  Goals.md / Guardrails.md template wiring, new `Initiatives/`
  vault subdirectory, restructured `/agency setup` interview that
  walks the owner through all three layers, five new audit rules
  for strategic alignment, and a weekly strategic-plan health
  check skill.

### Changed — README

"Plan your next quarter" section adds a one-paragraph mention of
the three-layer strategic-planning model with a link to
`docs/StrategicPlanning.md`. The fourth bullet rewrites from
"Track progress with real observations" to "**Ask the testability
question** — every week the agency asks: *are these inputs
(Initiatives) moving the outputs (Interim Goals), and are the
outputs moving the outcomes (Goals)?* The answer is measurable,
not a vibes check."

### Spec header

Bumped from v0.22.1-spec to v0.22.2-spec. Companion-doc reference
added pointing to `StrategicPlanning.md`.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.1-spec] — 2026-05-24

**Spec revision: Goals.md (and the other agency-level context docs)
are always part of the background.** Pure spec + README clarification
— no code change. Makes explicit what was implicit: the 7-step
learning loop operates *with* the owner's declared goals and values
always present in the operating context, never the foreground, never
absent. The goals aren't the lens everything routes through; they're
the atmospheric pressure the agency works inside. Spec-only revision;
does not advance the 9th-version milestone counter.

### Changed — spec §1.1 (the seven-step learning loop)

The 7 steps themselves are unchanged. Added a closing paragraph
naming the agency-level context docs (Goals.md, Values.md,
Personal.md, Work.md, Clients.md, per-profile SOUL.md) as the
always-loaded background. The framing makes it clear the agency
never operates in a vacuum without becoming a goal-attribution
audit system layered over the learning loop.

### Added — §1.1.1 "Implementation state (context-injection)"

A short, honest section. As of v0.22, the round-trip infrastructure
for agency context docs exists separately from the learning code.
v0.23 adds an audit rule to confirm the always-loaded context block
actually includes the agency-level docs at skill-load time, plus an
optional `--goal <key>` flag on `/agency capture` for owners who
want to attach a specific goal to a correction.

### Changed — §1 promise, §1.7 systems table, §2.2 spine diagram

Each gets a light touch acknowledging the always-present context
docs:
- §1 promise: closing sentence names Goals.md, Values.md, etc. as
  "always part of the background the agency operates in — present
  every turn, not foreground, but never absent."
- §1.7 row 1: notes that the agency-level context docs are part of
  the always-loaded background alongside rule injection.
- §2.2 spine paragraph: notes that the context docs accompany rule
  injection at every skill load.

The 7 steps themselves, the systems table structure, and the spine
diagram are unchanged.

### Added — v0.23 closure-plan entry in §13.7

Scoped acceptance for the always-loaded agency-context audit:
- Audit rule (`agency-context-injection`) confirms agency-level docs
  are reachable from skill-load context.
- `/agency capture --goal <key>` flag for owners who want to attach
  a goal to a correction (optional, not required).
- Small prompt-injection format consistency change.

This is much smaller than a goal-attribution system layered over
the learning loop — it just verifies the always-present-background
claim is testable.

### README

Intro paragraph: closing sentence acknowledging Goals.md, Values.md
and the other context docs are "always part of the background the
agency operates in — present every turn, never the foreground,
never absent."

"Plan your next quarter" task-list section adds a one-line preamble
naming the always-present-context idea (light, not heavy).

System-1 description gets one trailing sentence about the
always-present context docs.

### README task-list adjustments (separate from goal-anchoring)

Per AJ's review:
- Dropped "weekly industry newsletter" bullet (not universally
  appealing); replaced with "Track conversations you've started
  and need to follow up on" (broader small-business pain).
- Dropped "Catch embarrassing send-mistakes" bullet (too
  negative-toned for marketing copy).
- Added "Stay on top of invoices, expenses, and late-paying
  clients" to the "Run your operations" category to surface the
  finance subsystem.

### Tests

- No code changed; no test churn (242 still passing).
- `agency audit --self`: clean.

## [0.22.0] — 2026-05-24

**PyPI publication + entry-point install** (v0.05 of the 9th
version — see spec §0.5). Closes the install loop from spec §13.7.
After this release, `pip install hermes-agency` registers the
plugin with Hermes automatically — no symlink at
`~/.hermes/plugins/hermes-agency/` required.

(v0.21 — profile registration + agentskills.io conformance — is
deferred. PyPI publication is the mechanical, well-understood
step; doing it first means subsequent releases can flow through
the normal `pip install --upgrade` channel.)

### Added — `[project.entry-points."hermes.plugins"]` declaration

`pyproject.toml` now declares:

```toml
[project.entry-points."hermes.plugins"]
hermes-agency = "hermes_agency_plugin:register"
```

Hermes' `PluginManager` enumerates `hermes.plugins` entry-points at
startup and calls `register(ctx)` on each resolved target. This is
Hermes' documented plugin-discovery contract — same surface as
`~/.hermes/plugins/<name>/` symlinks, but distribution-friendly.

### Changed — `bootstrap.sh` prefers PyPI

The one-command installer now tries `pip install hermes-agency`
first and falls back to editable-install from a git clone if PyPI
is unreachable or the package isn't published yet:

```bash
if [[ "$INSIDE_REPO" == "true" ]]; then
    # Developer path: editable install from the clone
    pip install -e "${TARGET}[dev,google,embed,ingest]"
else
    # Curl-pipe path: PyPI first, fall back to clone
    if pip install "hermes-agency[google,embed,ingest]"; then
        : # PyPI win
    else
        pip install -e "${TARGET}[dev,google,embed,ingest]"
    fi
fi
```

Effect: `curl ... | bash` becomes a `pip install` from PyPI in the
common case, and the install never re-clones the repo unless PyPI
itself is unavailable.

### Verified — wheel ships the entry-point

Built locally with `python -m build --sdist --wheel --outdir
/tmp/hermes-agency-build`. Inspected the resulting wheel's
`entry_points.txt`:

```
[console_scripts]
agency = hermes_agency.cli:main

[hermes.plugins]
hermes-agency = hermes_agency_plugin:register
```

Both entry-points present. The wheel is now ready to publish to
PyPI under the `hermes-agency` distribution name.

### Tests

- 242 passing (no test churn — entry-point declaration is
  metadata-only, no runtime path changes).
- `agency audit --self`: clean.

### What's NOT in v0.22

- **Actual `twine upload`** to PyPI happens out-of-band (requires
  PyPI credentials in operator's environment, not in the repo).
  Once uploaded, the `bootstrap.sh` PyPI-first path activates
  automatically for everyone running `curl ... | bash`.
- **v0.21 work** (profile registration + agentskills.io conformance)
  is still pending. The next release after v0.22 will pick that up.

The closure plan after v0.22:

  v0.21 (later) — Profile registration + agentskills.io conformance
  v0.23         — Directory rename `_framework/` → `hermes_agency_plugin/<x>/`
                  (final cosmetic alignment)

After PyPI publication, HermesAgency is install-complete: the
4-step recipe in the README — install Hermes, `pip install
hermes-agency`, `hermes`, `/agency setup` — works end-to-end without
any clone, symlink, or post-install fixup.

## [0.20.0] — 2026-05-24

**Parallel-state collapse.** Agency state moves from
`~/.agency/_state/` → `~/.hermes/agency-state/`, so HermesAgency
no longer owns a separate state world (per spec §13.7 v0.20 plan,
v0.04 of the 9th version).

### Changed — state resolution

`STATE_DIR` and `HEALTH_DIR` in `_framework/constants.py` now
resolve via three signals in priority order:

1. `$HERMES_AGENCY_STATE` env var (explicit operator override)
2. `~/.hermes/agency-state/` (v0.20+ default, when `~/.hermes/`
   exists)
3. `$AGENCY_HOME/_state/` (legacy fallback for pre-v0.20 installs)

Fresh installs land at the v0.20+ location automatically. Existing
pre-v0.20 deployments continue working at their legacy location
until the operator runs `agency migrate-state`.

### Added — `_framework/migration/state_collapse.py`

The one-shot migration module:

- `plan_state_collapse() → StateCollapsePlan` — inspects filesystem
  and reports which files would move. Detects three cases:
  - `already_migrated` (v0.20+ location has files, legacy is empty)
  - `nothing_to_migrate` (neither location populated — fresh install)
  - Files to move (legacy populated, v0.20+ empty or partial)
- `apply_state_collapse(plan) → StateCollapseResult` — performs the
  move. Atomic per-file. On collision, prefers the legacy version
  (operator's existing data). Writes a tombstone at
  `~/.agency/_state.MIGRATED-TO-v0.20` so future audits know the
  migration ran. Idempotent — re-running after success is a no-op.

### Added — `agency state-location` CLI command

Reports which state location the running framework resolves to,
plus a warning if legacy state is still present after migration:

```
agency state-location
HermesAgency 0.20.0 state locations:

  state dir:  /Users/<you>/.hermes/agency-state
  health dir: /Users/<you>/.hermes/agency-state/_health
  resolved via: v0.20+ default (~/.hermes/agency-state/)
```

### Added — `agency migrate-state` CLI command

Drives the state-collapse migration:

```
agency migrate-state plan         # preview what would move
agency migrate-state apply        # perform the move (with confirmation)
agency migrate-state apply -y     # skip confirmation
```

### Tests

- New `tests/seams/test_state_collapse.py` — 7 tests:
  - Fresh install (no legacy) — `nothing_to_migrate`
  - Legacy populated — plan lists files
  - v0.20+ populated, legacy empty — `already_migrated`
  - End-to-end apply (3 files including health) → moved + tombstone
  - Idempotency (second apply is no-op)
  - Constants resolve to v0.20+ location when `~/.hermes/agency-state/`
    exists
  - Explicit `$HERMES_AGENCY_STATE` override wins
- 242 passing total (was 235).
- `agency audit --self`: clean.

### What's NOT in v0.20

Two pieces from the original v0.20 plan are deferred to subsequent
releases as their own focused work:

- **Directory rename** (`_framework/<x>/` → `hermes_agency_plugin/<x>/`)
  is cosmetic relative to the user-visible state-collapse and would
  touch every file via import-path updates. Deferred to v0.23
  (post-PyPI) when it can be a deliberate single-commit refactor with
  full import-path audit.
- **Profile registration via `ctx.register_agent`** needs research
  into Hermes' agent-registration API surface; deferred to v0.21
  alongside the agentskills.io conformance work where the
  registration shape will become clearer.

The closure plan is now:

  v0.21 — Profile registration + agentskills.io conformance
  v0.22 — PyPI publication + entry-point install
  v0.23 — Directory rename `_framework/` → `hermes_agency_plugin/<x>/`
          (final cosmetic alignment)

## [0.19.0] — 2026-05-24

`/agency setup` becomes a real interactive interview inside Hermes
(v0.03 of the 9th version — see spec §0.5). The bash `agency init`
wizard is no longer the primary configuration surface; first-run
setup happens via `/agency setup` slash-command inside `hermes`.

Also: tagline sharpened to "**HermesAgency: The Agent Team Designed
for Solopreneurs & Small Businesses** — Powerful Autonomous Team.
Continuous Context Learning. Complete Privacy & Data Control."

### Added — `hermes_agency_plugin/setup/` module

State-machine for the in-Hermes setup interview. Three files:

- `state.py` — `SetupState` dataclass, `load_state` / `save_state` /
  `clear_state` / `is_configured` / `mark_configured`. State
  persisted at `~/.hermes/agency-state/.setup-state.json` (v0.20
  target) with fallback to `~/.agency/.setup-state.json` for
  pre-v0.20 deployments.
- `interview.py` — `handle_setup_command(rest)` routes the
  subcommands; 8-question clean-install flow; migration path that
  invokes `migrate_v7_full(<path>)`.
- `__init__.py` — public surface.

### `/agency setup` subcommands

```
/agency setup                           Show the migration-or-clean menu
/agency setup status                    Report current setup state
/agency setup migrate <v7-path>         Pull data from a prior install
/agency setup clean                     Start the clean-install interview
/agency setup answer <text>             Answer the current question
/agency setup reset                     Wipe in-progress state, start over
/agency setup help                      Show menu (same as no args)
```

Mid-interview, calling `/agency setup` re-shows the current question.

### Clean-install interview — 8 questions

In order, each writing to a specific vault file at the end:

1. Owner name             → `Personal.md`
2. Organization name      → `Work.md`
3. Role description       → `Work.md`
4. Current goals          → `Goals.md`
5. Values                 → `Values.md`
6. Personal context       → `Personal.md`
7. Clients                → `Clients.md`
8. Voice notes            → `SOUL-voice-notes.md`

Any question accepts `skip` to omit; the framework reads existing
vault files and treats absence as "no constraints in this domain
yet." Operators can edit any of these files directly afterward.

### Migration path

`/agency setup migrate <v7-path>` invokes `migrate_v7_full(<path>,
profile=<current>)` — the same code path as the shell-side
`agency migrate v7 apply`. Imports learning corpus + SOULs +
standards + vault MDs + legacy DBs. On success, writes
`.configured`. On failure, surfaces the error and preserves the
in-progress state for re-run.

### `.configured` marker

Written to `~/.hermes/agency-state/.configured` (or `~/.agency/
.configured` on pre-v0.20 deployments) when either path completes
successfully. The marker prevents `/agency setup` from re-prompting
and is read by `/agency status` and `agency next` to determine
deployment readiness.

### Tagline change

The product tagline + positioning sharpened to the v0.18.2-spec
formulation:

- **Main:** "HermesAgency: The Agent Team Designed for Solopreneurs
  & Small Businesses"
- **Three pillars:** "Powerful Autonomous Team. Continuous Context
  Learning. Complete Privacy & Data Control."
- Updated in README, pyproject.toml description, plugin.yaml
  description, and the spec.

### Tests

- New `tests/seams/test_setup.py` — 9 tests covering: initial
  prompt, clean-install advance-through-all-8-questions, skip
  answers, status, already-configured blocking, reset, migrate
  needs path, mid-interview resume, /agency dispatch routing.
- 235 passing total (was 226).
- `agency audit --self`: clean.

## [0.18.0] — 2026-05-24

Verifier enforcement + deprecated-patches removal (v0.02 of the 9th
version — see spec §0.5 for lineage).

### Added — `transform_tool_result` hook (verifier enforcement)

The plugin's `post_tool_call` hook recorded observations through
v0.17. v0.18 adds `transform_tool_result` — Hermes' documented hook
for plugins that want to rewrite a tool's result before it goes back
to the LLM.

For tools that produce a verifiable filesystem artifact
(`write_file`, `patch`, `edit_file`), the hook constructs ad-hoc
verifier criteria from the tool args:

- `write_file(path=X)` → `file_exists` criterion on X
- `patch(path=X, new_string=Y)` → `file_exists` + `file_contains`
  (verifying Y is now in X)
- `edit_file(path=X, content=Y)` → same as patch

Failed criteria get rewritten into actionable LLM errors:

```
[HermesAgency verifier — TOOL OUTPUT FAILED VERIFICATION]

Tool 'write_file' returned success, but the verifier caught
1 criterion failure(s):

  - file_exists: /tmp/output.txt not found

Original tool result (for debugging):
{"ok": true}

Either fix the issue and re-run the tool, or explain in your
response why this failure is acceptable for the task.
```

This is v0.18 generic enforcement; v0.21 will add per-skill
criteria pulled from the active skill's frontmatter once Hermes'
agentskills.io integration exposes skill-execution context to
plugin hooks.

### Removed — `_framework/hermes_patches/` module

Deprecated in v0.17 (REGISTRY was already empty); deleted entirely
in v0.18. The text-anchor patch approach used through v0.16 is fully
retired.

- Module deleted: `_framework/hermes_patches/` (5 files)
- Test file deleted: `tests/seams/test_hermes_patches.py`
- 3 auto-reapply tests deleted from `tests/seams/test_quality_and_cost.py`
- `SYSTEM_INVENTORY` moved to `hermes_agency_plugin/system_inventory.py`
  (where it logically belongs as part of the plugin's honesty surface)

### Changed — `agency hermes-patches` subcommand

The `systems` action keeps working (it's the public honesty
surface) and now reads from the plugin's inventory. The
`apply` / `status` / `list` subcommands print a retirement
notice explaining the v0.17 plugin pivot — kept for graceful
deprecation rather than removed entirely.

### Tests

- 226 passing (was 224 with 4 skipped). The 4 skipped patches-
  tests are now actually deleted, hence 4 removed + 2 retained
  v0.17 patches tests cut entirely. Net: same coverage on the
  live path, no skipped dead-code tests.
- 4 new tests in `tests/seams/test_plugin.py` cover the new
  `transform_tool_result` hook: write_file passing, write_file
  rewriting on missing file, patch with content-mismatch rewriting,
  read-only tools passing through.
- `agency audit --self`: clean.

## [0.17.0] — 2026-05-24

**Architectural pivot: HermesAgency is now a real Hermes plugin.**

While preparing to write text-anchor patches for the three missing
reliability systems (autonomy gate, verifier, send-guard), the search
through Hermes' source uncovered a documented plugin API with the exact
lifecycle hooks we need: `pre_llm_call`, `pre_tool_call`,
`post_tool_call`, `on_session_start`, `on_session_end`. Plugins drop at
`~/.hermes/plugins/<name>/`, get auto-discovered, register hooks and
slash commands via a `register(ctx)` function.

This release pivots HermesAgency from "framework that text-patches
Hermes' source" to "Hermes plugin that registers hooks via the API."
Same goal, dramatically better implementation. Hermes' internal
refactors no longer threaten our integration — the plugin API is a
stable contract.

### Added — `hermes_agency_plugin/` package

The Hermes plugin entry point. `register(ctx)` wires five lifecycle
hooks:

| Hook | Reliability system |
|---|---|
| `pre_llm_call` | #1 Supervised learning loop — injects applicable rules into the user message of every turn (preserves prompt cache; system prompt stays identical across turns) |
| `pre_tool_call` | #2 Autonomy ladder — consults `_framework.autonomy.get_skill_level` + `get_action_class_min_level`; returns a block-message string for refused tool calls |
| `pre_tool_call` (mail tools) | #6 Send-guard — filters for outbound-mail tool names, constructs a `SendCandidate`, runs `_framework.send_guard.evaluate`, blocks on hard-rule violations or access-list deny |
| `post_tool_call` | #3 Verifier — records tool completion to events.db (v0.17 = observation); v0.18 adds `transform_tool_result` for enforcement |
| `on_session_start` / `on_session_end` | #4 System Sentinel — records session events to agency events.db |

Plus `/agency` slash command — runs inside `hermes chat` for the
supervisory surface (status, capture, audit, systems, learn list,
setup stub).

### Added — `agency hermes-patches systems` reports 7/7 wired

All seven reliability systems are now Hermes-extending:

```
HermesAgency — 7 reliability systems (integration state)

  ✓ Supervised learning loop          wired (Hermes-native — plugin hook)
  ✓ Autonomy ladder (L1–L5)           wired (Hermes-native — plugin hook)
  ✓ Verifier (per-skill criteria)     wired (Hermes-native — plugin hook)
  ✓ System Sentinel                   wired (Hermes-native — plugin hooks)
  ✓ Kanban tracks-link type           wired (Hermes-native shim)
  ✓ Send-guard (outbound mail gate)   wired (Hermes-native — plugin hook)
  ✓ Audit (weekly alignment check)    wired (Hermes-native — script)

  7 / 7 systems are actually Hermes-extending.
```

### Changed — bootstrap.sh installs plugin via symlink

The new bootstrap step:

1. Verifies Hermes is on PATH (Step 1 of the install must be done first)
2. Optionally `--reset` wipes prior agency state
3. Clones / pip-installs HermesAgency
4. Symlinks `~/.hermes/plugins/hermes-agency/` → `<repo>/hermes_agency_plugin/`
5. Hermes auto-discovers on next launch

Plugin discovery happens at Hermes start — no `agency hermes-patches
apply` step needed. The bootstrap script's `--apply-patches` flag is
preserved for the symlink registration; default is on.

### Deprecated — text-anchor patches

`_framework/hermes_patches/skill_load_injection.py` and the
`apply_all` / `check_status` / `auto_reapply` machinery are
**deprecated**. The REGISTRY is now empty by design; the module
is kept as a no-op for one release so v0.16 deployments don't
break. **Removed in v0.18.**

4 tests are now `@pytest.mark.skip`-ed with deprecation rationale
(3 in test_hermes_patches.py, 1 in test_quality_and_cost.py). The
test files themselves get deleted alongside the module in v0.18.

### Tests

- New `tests/seams/test_plugin.py` — 10 tests covering the plugin
  surface: import, `register()` signature, hook registration, hook
  fail-open behavior on missing deployment, slash-command dispatch,
  context resolver.
- 224 passing, 4 skipped (deprecated text-patch tests).
- Audit clean.

### Roadmap update (§13.6 of the spec)

The closure plan is now narrower and faster:

- **v0.18** — verifier enforcement via `transform_tool_result` hook
  (rewrite failed-verifier outputs into actionable LLM errors)
- **v0.18** — delete `_framework/hermes_patches/` deprecated module
- **v0.19** — `/agency setup` interactive interview (migration-or-clean-
  install) as a real in-Hermes slash command — replaces the deferred
  v0.20 "agency setup CLI" plan
- **v0.20** — parallel-state collapse (move `~/.agency/_state/*.db` to
  `~/.hermes/agency-state/` sidecar) so the framework owns no separate
  state world

## [0.16.0] — 2026-05-24

The 4-step install. AJ asked for the simplest possible install
roadmap: (1) install Hermes, (2) install plugin, (3) migrate v7,
(4) type `hermes` and it works. v0.16.0 delivers exactly that.

### The new install path

```bash
# 1. Install Hermes (NousResearch's official installer)
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. Install HermesAgency plugin (auto-applies patches)
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash

# 3. Migrate v7 (optional)
agency migrate v7 apply --from ~/.hermes-v7-backup

# 4. Use it
hermes
```

### Changed — bootstrap.sh is plugin-only

The bootstrap script no longer installs Hermes. Plugin discipline
(§1.4 of the spec): the framework does not install its own
runtime. If `hermes` isn't on PATH, bootstrap.sh prints a clear
error pointing at NousResearch's installer and exits 1.

Removed: `--reset-deep` (no longer relevant — the bootstrap doesn't
install Hermes, so there's nothing "deep" to reset).

Added: `--no-patches` flag to skip the auto-apply step (for users
who want to inspect patch status before applying).

The bootstrap's "Done" footer now leads with the canonical sequence:
`agency hermes-patches systems` → `agency migrate v7 ...` → `hermes`.

### Changed — wizard drops the install-Hermes path

`_framework/ops/init/wizard.py::_hermes_step` no longer offers to
install Hermes for the user. Branch B (install fresh) is removed.
Only Branch A (detect existing) remains. If Hermes isn't detected,
the wizard refuses with a pointer to NousResearch's installer and
returns exit code 3.

The legacy `_framework/hermes_engine/installer.py` module is kept
(used by `agency init --hermes-only` recovery + tests) but no
wizard path invokes it. It will be deprecated and removed in v0.17.

### Added — `agency migrate v7 --from <directory>` (full migration)

The migrate command now accepts a v7 home DIRECTORY in addition to
a `loriah.db` file:

```bash
# Full migration (directory mode — new in v0.16)
agency migrate v7 apply --from ~/.hermes-v7-backup --profile loriah

# Legacy mode (file argument) still works
agency migrate v7 apply --from ~/.hermes-v7-backup/.hermes/context/loriah/Admin/loriah.db
```

In directory mode, the migration does:

1. Learning corpus migration (the existing v0.7 behavior)
2. Copy `Soul.md` → `~/.agency/profiles/<id>/SOUL.md`
3. Copy `standards.md` / `stewardship.md` → `~/.agency/profiles/<id>/standards.md`
4. Copy `Goals.md` / `Values.md` / `Personal.md` / `Work.md` /
   `Client.md` / `Loriah.md` / `Governance.md` → `~/.agency/
   profiles/<id>/vault/`
5. Copy `book_coaching.db` / `bizdev.db` / `quality.db` /
   `hardware-watch.db` → `~/.agency/_state/v7-legacy/`

Auto-discovers the v7 layout under several common shapes:
`<v7_home>/.hermes/context/<profile>/Admin/`,
`<v7_home>/context/<profile>/Admin/`,
or `<v7_home>/Admin/`.

New `_framework/migration/v7_full.py` module carries
`migrate_v7_full()`, `discover_v7_admin_dir()`, and
`V7FullMigrationResult`.

### Changed — README is the 4-step recipe

The README's first content (after the badges) is now the literal
4-command install path. Everything else — architectural framing,
plugin discipline, supervisory commands, advanced options — is
below the fold.

### Tests

218 passing. Audit clean.

## [0.15.0] — 2026-05-24

Plugin framing restored. AJ pointed out that the project had
drifted from "Hermes plugin that adds 7 reliability systems" into
"parallel framework with its own chat, panel, state, and runtime."
The spec's first sentence said *layered on top of Hermes* — what
got built was *next to Hermes*.

This release doesn't ship new features. It corrects the narrative
+ the surfaces. The next two releases (v0.16+) will close the
actual integration gaps (missing patches for autonomy gate,
verifier, send-guard).

### Added — `agency hermes-patches systems`

The honest 7-system integration inventory. Output for a fresh
install today:

```
HermesAgency — 7 reliability systems (integration state)

  ✓ Supervised learning loop          wired into Hermes (patch)
  ✗ Autonomy ladder (L1–L5)           PATCH NOT YET BUILT — parallel
  ✗ Verifier (per-skill criteria)     PATCH NOT YET BUILT — parallel
  ✓ System Sentinel                   wired (Hermes-native shape)
  ✓ Kanban tracks-link type           wired (Hermes-native shape)
  ✗ Send-guard (outbound mail gate)   PATCH NOT YET BUILT — parallel
  ✓ Audit (weekly alignment check)    wired (Hermes-native shape)

  4 / 7 systems are actually Hermes-extending.
```

The `SYSTEM_INVENTORY` constant in `_framework/hermes_patches/
apply.py` is now the source of truth for "what does HermesAgency
*claim* to extend, and is each claim actually wired?"

### Changed — README restructured around plugin framing

Tagline changed from "A multi-agent framework for small-agency
owners..." to "A Hermes plugin that adds 7 reliability systems
for small-agency owners..."

"How you use it" section leads with `hermes chat`, not `agency
chat`. Three commands in the canonical order:

```
agency hermes-patches apply     # one-time wiring
agency hermes-patches systems   # see what's wired
hermes chat                     # use the engine — now enriched
```

### Demoted — `agency chat`

Marked as **diagnostic surface**, not daily-use. Prints a banner
on every invocation:

```
─────────────────────────────────────────────────────────────
 DIAGNOSTIC SURFACE — this is not how you normally use HermesAgency.
 For daily use:  hermes chat  (with patches applied)
 See:            agency hermes-patches systems
─────────────────────────────────────────────────────────────
```

`--no-banner` suppresses the banner for scripted use. The command
still works (it's useful for testing rule injection / SOUL loading
without going through Hermes), but the README + CLI help direct
users to `hermes chat` for normal use.

### Demoted — `agency panel`

Reframed in docs as a read-only diagnostic UI, not a primary
surface. (No code changes — just no longer the answer to "how do
I use the framework.")

### Changed — bootstrap.sh post-install message

The "Done" footer now points users at the canonical sequence:

```
agency hermes-patches apply    # one-time per Hermes upgrade
agency hermes-patches systems  # see which of the 7 are wired
hermes chat                    # this is how you run it
```

### Architectural roadmap (the actual fix is v0.16+)

v0.15.0 closes the *narrative* gap. The 3 missing patches still
need to be built — those are real engineering, each one a
release-sized chunk:

- **v0.16.0** — `autonomy-gate` patch: pre-action hook in Hermes'
  skill executor that calls `_framework.autonomy.allowed(...)`
  before consequential actions
- **v0.17.0** — `post-completion-verifier` patch: post-skill hook
  that runs `_framework.verifier.run(...)` on the output
- **v0.18.0** — `outbound-mail-guard` patch: pre-send hook on
  Hermes' email path that calls `_framework.send_guard.check(...)`
- **v0.19.0** — collapse parallel state where possible (learning
  rules, events) into sidecar tables Hermes can read directly

### Tests

218 passing. Audit clean.

## [0.14.0] — 2026-05-24

`agency chat` — the framework's first built-in inference path.
First-time users have a "type something, get a real response from
your CoS" surface, with SOUL + standards + all applicable v7-
migrated learning rules loaded into the prompt automatically.

### Added — `_framework/runtime/` subsystem

Three modules. Stdlib-only (urllib + json) — no new dependencies.

- `provider.py` — `ResolvedProvider` config resolver. Reads
  `deployment.yaml::defaults` + `credentials`, resolves
  `env:VAR` / `keychain:NAME` / `file:PATH` / `-` credential
  references. Refuses raw secrets in the credential field
  (raises `ProviderResolveError` with guidance).

- `prompt.py` — `compose_chat_prompt(profile, role, voice_tags,
  skill_tag)` returns a `ComposedPrompt`. Stacks: SOUL.md →
  standards.md → applicable learning rules (via the existing
  `inject_for_skill()` resolver) → session framing footer.
  Tells the agent to cite rule ids it uses (which records firings
  for the recapture detector).

- `chat.py` — `chat_once(message)` for one-shot, `repl()` for
  interactive. Standard chat/completions HTTP call. Vendor-neutral
  — names no provider in code (framework-vendor-leak audit
  enforced).

### Added — `agency chat` CLI command

```bash
agency chat                                       # interactive REPL
agency chat "draft a polite decline note"         # one-shot
agency chat --profile lynda --verbose "..."       # talk to a different profile, show
                                                  # provider/model/rules/tokens after
```

Flags: `--profile`, `--role`, `--voice-tags=a,b,c`, `--skill-tag`,
`-v/--verbose`.

This is the answer to "how do I actually USE this thing?" — works
the moment a deployment has a configured provider, regardless of
whether Hermes' cron jobs have fired anything yet. Hermes is still
the autonomous runtime for scheduled skill execution; `chat` is
the interactive surface for the operator.

### Tests

- 10 new tests in `tests/seams/test_runtime.py` covering credential
  resolution (env / dotenv / file / keychain / raw-rejection) and
  prompt composition (no-files fallback, SOUL inclusion, standards
  inclusion, framing footer).
- 218 passing total (was 208).
- `agency audit --self`: clean.

### Docs

- README quickstart adds a "Talk to your agency" section after the
  wizard, leading with `agency chat` as the smoke-test surface.

## [0.13.2] — 2026-05-24

Repo went public. Docs updated to lead with the curl-pipe
one-liner now that auth isn't a barrier.

### Repository visibility

`github.com/ajcrabill/hermes-agency` flipped from private to public
(MIT-licensed). The bootstrap.sh one-liner is now reachable without
GitHub auth:

```bash
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash
```

### Updated docs

- README: leads with the curl-pipe one-liner front-and-center,
  followed by quickstart sections for after-the-wizard, tier
  choices, hermes-only resume, reset, and a manual-install
  fallback. License + Python + Hermes badges added.
- bootstrap.sh header: documents all three invocation modes
  (curl-pipe, git-clone-and-run, in-repo) since they all work
  now.
- DEPLOYMENT.md: "One-command (recommended)" section with the
  curl-pipe lead; manual install demoted to a fallback section;
  full flag reference moved here.

### Pre-public secrets sweep

Verified before flipping visibility — no API keys committed
(no `sk-*`, `pk-*`, `xoxb-*`, `ghp_*`, `AIza*`, `AKIA*` shapes
anywhere in tracked files). The only emails in the repo are AJ's
public contact at `aj@ajcrabill.com` (pyproject.toml `authors`
field) and a few `*@gmail.com` deployment examples in the spec
doc that AJ wrote with his real addresses on purpose. No `.env`
or credential files committed.

### Tests

208 passing. Audit clean.

## [0.13.1] — 2026-05-24

One-command installer. AJ asked: "what's the single command for
fresh-install (wipe + clone + Hermes detect-or-install + agency
setup)?" Three pieces ship to make that real.

### Added — `bootstrap.sh`

A self-contained shell script at the repo root. End-to-end:

  1. (`--reset`) wipe `~/.agency`, `~/.agency-venv`, `~/.hermes`,
     `~/.hermes-v7-snapshot`, `~/.hermes-engine-venv`
  2. (`--reset-deep`) also wipe `~/HermesAgency`,
     `~/.local/bin/hermes`, `~/agency-staging`
  3. Preflight: python 3.11+, git
  4. Clone HermesAgency (if not run from a checkout)
  5. Create venv at `~/.agency-venv`
  6. `pip install -e` with `[dev,google,embed,ingest]` extras
  7. Run `agency init` — which starts with Branch A/B (detect or
     install Hermes), then continues into the T1 wizard

One-paste fresh-install (private repo, SSH-auth machine):

```bash
git clone https://github.com/ajcrabill/hermes-agency.git /tmp/ha-bootstrap \
  && bash /tmp/ha-bootstrap/bootstrap.sh --reset
```

Flags: `--reset` / `--reset-deep` / `--no-init` / `--target=<dir>`
/ `--venv=<dir>` / `--hermes-home=<dir>` / `--ref=<branch>` /
`--skip-deps`.

### Added — `agency reset` command

For wiping an existing deployment without leaving the venv:

```bash
agency reset                       # wipes ~/.agency
agency reset --include-hermes      # also wipes ~/.hermes
agency reset --include-v7-snapshot # also wipes ~/.hermes-v7-snapshot
agency reset --include-venv        # also wipes ~/.agency-venv
agency reset -y                    # skip confirmation prompt
```

Prompts "Type 'wipe' to confirm" before deleting unless `-y`.

### Fixed — `install.sh` stale "0.1.0" hardcode

Same bug as the wizard's earlier framework_version fix. install.sh
hardcoded `echo "0.1.0" > framework-version.lock`. Now reads
`_framework.__version__` at install time.

### Tests

208 passing. Audit clean.

## [0.13.0] — 2026-05-24

Hermes-as-first-class-prerequisite. The wizard now starts with a
Branch A/B choice (detect existing Hermes, or install Hermes for
you), and the framework refuses to pretend it's a valid deployment
when there's no engine to layer onto.

### Added — `_framework/hermes_engine/` subsystem

Two modules:

- `detection.py` — single source of truth for "is Hermes here? where?"
  Signals (priority order): `$HERMES_HOME` env var → `~/.hermes`
  default → `hermes` on `PATH`. A "valid Hermes home" has any of
  `hermes-agent/`, `state.db`, `kanban.db`, or `scheduler.db`.
  Returns a `HermesInfo` dataclass with version, binary path, source
  dir, and which signal fired.

- `installer.py` — bootstraps a fresh Hermes install. Steps:
  prerequisites check (python 3.11+, git), git clone from
  `github.com/NousResearch/hermes-agent`, create venv, `pip install -e`,
  symlink binary to `~/.local/bin/hermes`, init HERMES_HOME, verify.
  Idempotent — re-running against an existing install does
  `git fetch` + `pip install --upgrade`.

### Added — Branch A/B in the init wizard

The wizard's first step (before owner/email/provider/etc.) is the
Hermes step:

1. Auto-detect. If found, confirm and use it.
2. Otherwise offer three options:
   - [a] Point at an existing install at a non-default path
   - [b] Install Hermes fresh (clone + venv + pip install -e)
   - [q] Quit and run `agency init` again later

Either branch populates a new `engine:` block in `deployment.yaml`:

```yaml
engine:
  hermes_home:     "/Users/agency/.hermes"
  hermes_binary:   "/Users/agency/.local/bin/hermes"
  hermes_version:  "Hermes Agent v0.14.0 (2026.5.16)"
  install_source:  "fresh-clone:https://github.com/NousResearch/hermes-agent.git@main"
```

### Added — `agency init --hermes-only`

Runs just the Branch A/B step. Useful when:
- HermesAgency was installed but Hermes wasn't (the "I went out of
  order" recovery path)
- You moved a deployment to a new machine and need to rebootstrap
  the engine without re-running the full wizard

Writes the `engine:` block in-place if `deployment.yaml` already
exists.

### Improved — `agency status` surfaces Hermes detection front + center

Status now prints a `Hermes engine:` section at the top of the
report. If detected, shows version + home + binary. If missing,
prints a loud ✗ with the resume command. Non-zero exit if either
Hermes is missing or the manifest is invalid.

### Improved — `agency next` treats Hermes-missing as a BLOCKER

Hermes detection is the first check in `agency next` and gets
priority #1 in the output if absent.

### Improved — `agency hermes-patches` / `agency cron sync` refuse cleanly

Previously these commands silently no-op'd or wrote to non-existent
paths when Hermes wasn't installed. Now both hard-error with a
clear "Hermes engine not detected — install with `agency init
--hermes-only`" message and exit 1.

### Schema — `deployment.yaml::engine` block

Validator surfaces a `warning` if the `engine:` block is missing
entirely, and a `warning` per missing key inside it. Not an error
yet (back-compat with pre-v0.13 deployments) — a future major
version may upgrade these to blocking errors.

### Tests

- New `tests/seams/test_hermes_engine.py` — 10 tests covering
  detection across signal priorities (env / default-home /
  path-binary-only) and installer prerequisites.
- Total suite: 208 passing (was 198).
- `agency audit --self`: clean.

### Docs

- README quickstart leads with "you do not need Hermes installed
  first — wizard does it for you (Branch B)."
- DEPLOYMENT.md prerequisites updated to drop the standalone
  Hermes install requirement and explain the A/B model.

## [0.12.2] — 2026-05-24

Four more UX/security patches from AJ's live install on esblaptop-m4.

### Fixed — wizard hardcoded `framework_version: "0.1.0"`

`_framework/ops/init/wizard.py` and `templates/deployment.yaml.template`
both hardcoded "0.1.0" into the generated manifest, regardless of
the actual framework version. This caused `agency status` to flag
the deployment as version-mismatched against a 0.12.x framework.
Now reads `_framework.__version__` at write-time and writes the
real version. `framework-version.lock` likewise.

### Fixed — wizard accepted raw API keys into credential field

The credential-reference prompt explained "keychain:NAME or
env:VAR" but didn't validate the input. AJ pasted his DeepSeek
API key directly; the wizard saved it inline into
`deployment.yaml::credentials.deepseek` where it sat in a
world-readable file.

Now: `_looks_like_raw_secret()` detects common API-key shapes
(sk-*, pk-*, xoxb-*, ghp_*, AIza*, AKIA*, plus a high-entropy
fallback for 32+-char alphanumeric strings) and re-prompts with
guidance. The wizard now also auto-creates `~/.agency/.env`
(chmod 600) with a stub so users have somewhere to paste the
raw key the env: ref will read from.

### Fixed — `agency events --tail N` ergonomics

`--tail` was `action='store_true'`. `agency events --tail 10`
errored "unrecognized arguments: 10". Now `--tail` uses
`nargs='?'` so all three shapes work:

  - `agency events`           — one-shot recent feed
  - `agency events --tail`    — stream new events for --duration
  - `agency events --tail 10` — stream, with rows-per-fetch
                                capped at 10

### Fixed — case-inconsistent profile IDs

The wizard prompted "System Sentinel profile id" (capital S in
the role name) with default `sentinel` (lowercase). AJ saw the
capitalized role and pressed Enter expecting `Sentinel`; got
`sentinel`. Meanwhile he typed `Loriah` and `Esby` capitalized,
ending up with a deployment that mixed `profiles/Loriah` and
`profiles/sentinel`.

Now the wizard adapts the lowercase defaults to match the case
style of the FIRST profile id the user types (`Loriah` →
`Sentinel`, `loriah` → `sentinel`). A tip about the convention
prints before the first prompt. If the final IDs still mix
case, the wizard warns at end with the rename commands.

### Tests

- 198 tests passing; new helpers unit-smoke-tested.
- `agency audit --self`: clean.

## [0.12.1] — 2026-05-24

UX patch from the first real install (AJ on esblaptop-m4).
Two specific gaps closed: T2 wizard didn't tell users how to
come back to deferred OAuth setup, and after init+migration
completed there was no clear "what to do next" surface.

### Added — `agency next` command

A new top-level command that reads deployment state and prints
actionable next-steps. Surfaces blockers (no LLM provider,
manifest errors), setup gaps (deferred integrations, empty
learning corpus), and optional steps (no cron jobs synced).
Each item ships with the exact command to run.

Designed to answer "what do I do now?" at any point in a
deployment's lifecycle. Healthy deployments get a "things you
can do" menu instead of blockers.

### Improved — T2 wizard end-of-flow

The wizard now prints, for every deferred integration, the
*exact* command to resume setup later — with the right
`--profile` value baked in. Previously it just listed deferred
items by name, leaving users to guess the resume path. Adds a
"What to do next" section with concrete first steps (wire LLM
provider, verify deployment, optional v7 migration, control
panel).

### Improved — `agency status` integration summary

Now prints per-profile integration state (gmail ✓ / calendar – /
drive – / signal – / slack –) alongside manifest validity, plus
a footer pointing at `agency next`.

### Tests

- 198 tests passing (no test regressions; new code paths are
  CLI-surface and covered by smoke-testing).
- `agency audit --self`: clean.

## [0.12.0] — 2026-05-24

Polish-for-git release. Spec moves into the repo. Five new
opportunity-hunting skills land across KB, Writing, and BD.

### Added — Spec in repo (`docs/HERMES_AGENCY_SPEC.md`)

- The HermesAgency design spec, previously living in AJ's v7 vault,
  is now versioned in the repo alongside `docs/ARCHITECTURE.md` +
  `docs/AUTONOMY.md` + the rest. The spec is the living source of
  truth for *design*; this CHANGELOG remains the user-facing
  *release* log.
- §16 change-log section rolled forward with all eleven
  release-level revisions (v0.1.0 → v0.11.0) plus a
  `v0.11-spec.0` entry marking the move into the repo.
- Title rolled from "v0.1 Specification" to "Specification" —
  the spec is no longer a one-version artifact.
- Generic path reference `~/.<owner>/...` replaces a v7-specific
  literal in §8.3 (keeps the audit clean).

### Added — KB weekly-industry-newsletter skill

`templates/profiles/knowledge-base/skills/_reference/weekly-
industry-newsletter.md` — Friday-AM personalized intelligence brief.
Distills KB's understanding of the principal's industry / goals /
IP / interests / thought-leadership areas; scours the past seven
days; clusters survivors into themed sections with
why-this-matters-to-you framing; drafts in the principal's reading
voice; hands to CoS lane (KB never sends outbound mail).
Repetition-avoidance against the last 3 weeks of newsletters;
diversity check on source mix; hard cap of 12 items / 6 sections.

### Added — Writing thought-leadership-scanner skill

`templates/profiles/writing-support/skills/_reference/thought-
leadership-scanner.md` — continuously hunts for thought-leadership
opportunities in the principal's addressable market.
*Highly curated, not generic.* Two phases: Phase 1 (niche discovery,
runs quarterly) helps the principal name their niche even if they
haven't yet; Phase 2 (opportunity hunting, runs daily) scores
candidates on niche-fit / audience-fit / effort-to-payoff and cuts
aggressively (target: ≥70% cut rate). Surfaces a weekly Friday
brief of ≤5 survivors with angles + a pitch draft for the top
opportunity. Generic-thought-leadership pitches are refused;
adjacency-trap mitigations enforced.

### Added — BD existing-client-commonality-analyzer skill

`templates/profiles/business-development/skills/_reference/
existing-client-commonality-analyzer.md` — weekly Monday-AM
analysis of signed/active clients to surface ICP commonalities
across organizational shape, industry, trigger, buyer persona,
engagement style, price point, IP exposure, and relationship
pathway. Scores patterns on coverage / strength / retention-
correlation; surfaces strong + emergent + drift signals. Output
feeds prospect-research and referral-opportunity-scanner via an
IP-corpus entry KB curates.

### Added — BD referral-opportunity-scanner skill

`templates/profiles/business-development/skills/_reference/
referral-opportunity-scanner.md` — weekly Tuesday-AM scan of
existing clients' professional networks for high-fit warm-intro
opportunities. Uses the ICP hypothesis from the commonality-
analyzer; scores connection-strength + recency; cuts to ≤3 per
week; drafts the actual ask message to the connecting client in
the principal's voice. Hard rule: max 1 ask per client per quarter;
honors a `do-not-approach.md` list unconditionally.

### Added — BD potential-clients-pipeline skill

`templates/profiles/business-development/skills/_reference/
potential-clients-pipeline.md` — the agency's patience engine.
Continuously maintains the potential-clients bench in
`_state/crm.db` (new `status='potential'` value joins the existing
enum); daily-AM picks 1–3 prospects warranting an action today
based on triggering events + open threads + cold-prospect cooling
periods; drafts the next message with prior-thread context loaded;
hands to CoS lane. 21-day per-prospect cooling enforced; max 3
nudges surfaced per day even if more could fire.

### Schema notes

- `_framework/crm/crm_db.py::leads.status` comment now includes
  `potential` alongside `new | active | doc-provided | no-interest
  | neutral | converted | dormant`. No migration needed; the
  column is free-text and new states light up as they're written.

### Tests

- 198 tests passing (no new test files added in this release —
  the new skills are markdown reference templates; their behavior
  surfaces through the existing skill-runner test infrastructure
  once a deployment activates them).
- `agency audit --self`: clean.

## [0.11.0] — 2026-05-24

Signal + Slack ingress, PyPI publishing prep, MANIFEST.in for
template distribution, CONTRIBUTING.md, Beta classifier.

### Added — Signal ingress (`_framework/integrations/signal.py`)

- Bridges to `signal-cli` (operator-installed); the framework
  shells out via JSON-RPC mode.
- `setup_interactive(profile, signal_number=...)` records the
  config without registering the number (operator runs
  `signal-cli register` + verify separately).
- `poll_messages()` and `send_message()` wrap the CLI.
- `signal_cli_available()` for graceful degradation when the
  binary isn't on PATH.

### Added — Slack ingress (`_framework/integrations/slack.py`)

- Uses Slack web API via urllib (no `slack_sdk` dependency — keeps
  the integration light + optional).
- Required scopes documented (chat:write, im:history, im:read,
  channels:history, users:read).
- `setup_interactive(profile, token=...)` resolves the bot user
  id via `auth.test` and stores both.
- `poll_messages()` reads DMs across all visible channels (bot's
  own messages excluded).
- `send_message()` posts to channel or DM with optional thread_ts.
- `open_im(user_id)` resolves a DM channel id.

### PyPI publishing prep

- **MANIFEST.in** — explicit inclusion of templates / docs /
  framework yaml / shared skills / install.sh. Tests included in
  sdist for downstream audit; build artifacts excluded.
- **CONTRIBUTING.md** — how to add bug reports, skills, subsystems,
  integrations, new roles. Coding conventions + vendor-neutrality
  rules + commit style + security reporting.
- **pyproject.toml** updates:
  - Development Status bumped Alpha → Beta
  - Optional-dependency groups renamed + expanded:
    `google` (api-client + auth-oauthlib),
    `voice` (faster-whisper),
    `ingest` (docx2txt + pdfplumber),
    `embed` (numpy)
  - `dev` adds `build` + `twine` for the release workflow
  - Removed the `openai` optional-deps name (operators pick their
    own client; framework is provider-neutral)

### Tests

198 passing (190 from v0.10.1 + 8 new Signal/Slack):
- 4 Signal tests (not-configured-default, setup-writes-config,
  poll-requires-config, send-requires-recipient)
- 4 Slack tests (not-configured-default, setup-resolves-bot-id-
  via-stub, send-requires-config, poll-degrades-on-api-failure)

Framework self-audit: 0 blocking, 0 warnings.

### PyPI publish flow (not yet pushed)

```bash
pip install build twine
python -m build         # builds sdist + wheel into dist/
twine check dist/*      # smoke-test PyPI metadata
twine upload --repository testpypi dist/*   # try TestPyPI first
twine upload dist/*     # then real PyPI
```

The framework is now Beta-classified. v1.0.0 will mark stable + the
first official PyPI release. Until then, `git clone + ./install.sh`
remains the documented path.

## [0.10.1] — 2026-05-24

Bug fix: v0.10.0 shipped with a `framework-vendor-leak` self-audit
finding. The pricing.py docstring used `"openai-compat"` as an
example provider id, which the audit rule (correctly) flagged as
a vendor name in framework code. Replaced with generic
`"<your-hosted-provider>"` placeholder. Self-audit now clean
again.

## [0.10.0] — 2026-05-24

Observation + delivery polish. Five subsystems landed in one round:

### Added — Two-tier quality auditor

- **`_framework/quality/`** — continuous (0.0-1.0) scoring per
  dimension (clarity, specificity, voice-fidelity, etc.) +
  rolling-score tracking per producer + auto-undelegation when
  a producer's rolling score drops below threshold across a
  window of artifacts.
- Composes with verifier: verifier = binary "complete?"; quality
  = continuous "how well?"
- Trust states: `trusted` (rolling ≥ 0.80) / `watching` (0.65-0.80)
  / `undelegated` (< 0.65). Framework proposes transitions;
  operator decides.

### Added — Cost / token attribution

- **`_framework/cost/`** — `inference_calls` ledger (per-call
  tokens-in/out + cost in micro-cents) + per-skill / per-role
  rollups + budgets (daily / weekly / monthly) with block-at-level.
- Pricing layer is operator-registered. Framework ships no
  hardcoded prices (vendor-neutral). Wildcard `model="*"` per
  provider for "all-local-models cost nothing" type rules.
- `check_budget()` returns a verdict per (skill, role, period)
  with current spend vs limit vs block-level.

### Added — Markdown projector (DB → vault regeneration)

- **`_framework/state/markdown_projector.py`** — solves the v7
  "vault and DB drift" problem (Appendix A.4 of spec). DB is
  canonical; vault is human-readable projection.
- Four built-in projectors (learning, goals, finance, prototypes)
  — each is a small function the framework can call. Operators
  register additional projectors via `register_projector(name, fn)`.
- Output lands at `agency-vault/projections/<name>/` with an
  `_index.md` aggregator.

### Added — Email-OTP auth on control panel

- **`_framework/ops/auth.py`** — 6-digit code, hashed for storage,
  10-minute expiry, 5-attempt lockout. 24h session tokens with
  revocation. Delivery via Gmail integration (operator's CoS profile);
  falls back to terminal display when Gmail isn't configured.

### Added — Auto-reapply Hermes patches

- **`_framework/hermes_patches/auto_reapply.py`** — fingerprints
  each patch target after a successful `apply_all()`. On the next
  `agency hermes-patches reapply`, if any target's fingerprint
  changed (Hermes upgraded + replaced our patches), the framework
  auto-reapplies and updates the lock.
- Operator adds `agency hermes-patches reapply` to their post-pip
  install wrapper. Real pip hooks remain in the v0.12+ bucket
  (pip's post-install story is messy).

### Tests

190 passing (171 from v0.9 + 19 new):
- 6 quality tests (continuous scoring with min-overall, rolling
  score, undelegation verdict across trust levels, not-enough-data
  guard)
- 4 cost tests (pricer registration + wildcard, record + rollup,
  budget overage detection)
- 2 projector tests (no-data safety, goals projection)
- 4 OTP auth tests (happy path, wrong-code reject, lockout, session
  revocation)
- 3 auto-reapply tests (no-lock = needs apply, fingerprint match,
  fingerprint change after stub Hermes upgrade)

Framework self-audit: 0 blocking, 0 warnings.

### Decisions logged

- Quality scoring uses **min(dimensions)** as overall, not the
  average. A chain is as strong as its weakest link — average
  rewards strong dimensions papering over weak ones.
- Cost storage in **micro-units** (1/1,000,000 of currency) for
  sub-cent precision on cheap models. Display layer divides.
- Markdown projector is **periodic, not real-time**. Operator's
  cron drives it; no live DB hooks needed. Cheap + simple.
- OTP delivery degrades gracefully — if Gmail isn't configured,
  operator sees the code in the terminal where `agency panel`
  runs (single-machine localhost flow remains usable).
- Auto-reapply uses a **shell wrapper**, not a pip hook. Pip's
  post-install hook story is deprecated + messy. The wrapper is
  transparent + operator-controllable.

## [0.9.0] — 2026-05-24

CoS gains the two things AJ called out: a **goal progress tracker**
(since SMART goals are measurable, measure them) and a **weekly
brainstorm** (3 actionable ideas per week for how HermesAgency
can autonomously help move toward the goals). Plus cleanup of
ObligationBoard + OpenWebUI references.

### Added — Goal tracking subsystem

- **`_framework/goals/tracking.py`** — `goal_tracking.db` with three
  tables: `goal_metrics` (what to measure + target + deadline +
  data source), `goal_observations` (recorded values over time),
  `goal_milestones` (interim bullets from Goals.md with deadlines
  + status).
- **`define_metric()`** — idempotent setup (re-defining a metric
  updates rather than duplicates).
- **`record_observation()`** + **`latest_observation()`** +
  **`observation_history()`** — append-only ledger.
- **`metric_status()`** — computes on-track / at-risk / missed /
  done / no-data per metric. Compares actual progress against
  expected linear pace toward the deadline. At-risk threshold
  defaults to 20% behind pace (operator-tunable via learning rule).
- **`weekly_status_report()`** — aggregate view across all metrics.
- **`sync_milestones_from_goals_md()`** — parses interim bullets
  out of `Goals.md::ANNUAL_GOALS`, extracts date hints (Q1/Q2/Q3/Q4
  → quarter-end, "by November 2026" → 2026-11-30, ISO dates
  preserved), upserts to `goal_milestones`.

### Added — Two new CoS skills

- **`goal-progress-tracker`** — Q&A coaching to set up metrics per
  goal (what's the measurable signal? what's the data source?),
  records observations on cadence, produces weekly status report
  with at-risk + missed surfaced first.
- **`weekly-brainstorm`** — produces three actionable ideas weekly
  for how HermesAgency can autonomously help reach the goals. One
  new-capability, one pattern-from-corrections, one resource-
  re-allocation. Each idea names the goal it serves, estimated
  cost, the signal that surfaced it, and a first concrete step.
  At least one must be about *stopping* something (not just
  starting). Honors `Goals.md::EXPLICIT_NON_GOALS` as a filter +
  the rejected-ideas list to avoid re-proposing.

### Added — `agency goals` CLI tracking actions

- `agency goals track --text "..." --metric ... --target N --target-at YYYY-MM-DD`
- `agency goals observe --metric ... --value N`
- `agency goals status` — colored on-track / at-risk / missed
  report, sorted with attention-items first
- `agency goals sync-milestones` — pull interim bullets from
  Goals.md into the tracking DB

Live-verified: created a goal, observed against it, status report
correctly shows on-track verdict with computed pace.

### Removed — deprecations

- **OpenWebUI** references removed from manifest validator hint,
  deployment.yaml.template, minimal-deployment example, T2 wizard
  flow + answers struct + persistence, owner-channels-ingress
  skill, wizard manifest renderer, test fixtures. Operators who
  want OpenWebUI integration make that call themselves; the
  framework doesn't pre-suggest it.
- **ObligationBoard** reference removed (was already deprecated
  before v7; the kanban handles obligation tracking via
  `tenant=obligation`).

### Tests

171 passing (159 from v0.8 + 12 new goal tracking tests):
- Define metric (basic + idempotent re-definition)
- Record + latest + history observations
- Status: on-track / at-risk / missed / done / no-data
- Weekly status aggregate
- Sync milestones from Goals.md (with date hint extraction)
- Mark milestone done
- Date hint variations (Q3, "November 2026", ISO date, vague)

Framework self-audit: 0 blocking, 0 warnings.

### How the new skills compose

The full intent→reality→improvement loop now closes:

  smart-goal-coach     →  defines SMART goals + interim milestones
  goal-progress-tracker→  measures progress against them
  time-use-analyzer    →  measures whether calendar matches priority
  weekly-brainstorm    →  proposes specific autonomous experiments

All four land in the weekly review, with at-risk + missed
surfaced first so they get attention rather than being buried.

### Skipped this round (per AJ direction)

- ObligationBoard re-introduction (deprecated; kanban handles it)
- OpenWebUI integration (operator's call, not the framework's)
- Multi-machine deployment + mesh layer (future)
- Additional roles beyond Finance (future)

## [0.8.0] — 2026-05-24

FinanceAgent role + finance subsystem. The seventh default role
(after CoS / KB / Sentinel / Analyst / BD / Writing). Per spec
§2.4 (N-agent expansion), demonstrates that adding a role is a
self-contained extension — no framework-internal changes beyond
listing the role in invariants.yaml.

### Added — Finance role

- `templates/profiles/finance/SOUL.md.template` — the agent's
  identity: precise, numerical, sourced; numbers without
  provenance are estimates and labeled as such
- `templates/profiles/finance/standards.md.template` — Job
  Description / Professional Standards (sourced-numbers-only,
  24h-book-currency, no-autonomous-money-movement, vendor-terms-
  are-commitments, bad-news-up, not-the-accountant) / Owned
  Deliverables / Include-Me / NOT-Include-Me / Collaboration /
  Conflict-Resolution
- `invariants.yaml::roles` adds `finance` with keywords:
  invoice, expense, revenue, budget, cash-flow, burn-rate,
  vendor-payment, reconcile, ledger, p-and-l, runway

### Added — `_framework/finance/`

- **`finance_db.py`** — five tables (invoices_in, invoices_out,
  expenses, revenue, vendor_payments) + budget_lines. Amounts in
  cents (integers — no float drift). Currency per-row. CRUD +
  overdue detection helpers.
- **`computations.py`** — `cash_position`, `monthly_burn`,
  `runway_months`, `revenue_attribution_summary`,
  `budget_vs_actual`. Pure read functions over the DB.

### Added — Seven finance skills

- **`cash-flow-tracker`** — current position / next-30 / next-90
  view with runway computation. Daily.
- **`burn-rate-monitor`** — rolling 3-month burn vs 12-month avg;
  flags trends up/down with category attribution. Weekly.
- **`invoice-management`** — prepare outbound, log inbound, follow
  up overdue with escalating cadence (3d / 7d / 14d / 30d), surface
  upcoming inbound for payment authorization. Money movement
  always requires owner authorization via CoS.
- **`revenue-attribution`** — trace each revenue row back to its
  originating outreach / referral / event. BD + owner see what's
  converting.
- **`expense-categorizer`** — apply operator's chart of accounts
  consistently. High-confidence matches auto-categorize; low-
  confidence surfaces for one-click classification (which
  captures as a learning rule).
- **`budget-vs-actual`** — monthly + quarterly variance reports.
  Sorted by absolute variance. Flags planned-but-unused (often
  the most actionable signal).
- **`quarterly-financial-summary`** — end-of-quarter package: P&L
  sketch, cash trend (≥4 quarters), runway, surprises, looking-
  forward. Goes through KB + Analyst review before external
  sharing.

### Tests

159 passing (148 from v0.7 + 11 new finance tests):
- Invoice lifecycle (in + out + paid linkage)
- Expense categorization
- Revenue attribution + by-source summary
- Cash position computation
- Monthly burn + runway (incl. undefined-when-no-burn case)
- Budget vs actual with variance %
- Overdue detection

Framework self-audit: 0 blocking, 0 warnings.

### How the role composes

Finance is the **seventh default role**. A deployment opts in by
adding to `deployment.yaml::profiles` (with `id`, `role: finance`,
`email: null` per the single-mailbox default — finance
correspondence flows through CoS like all other specialists).

Per spec §2.4, no framework internals required modification to
add it — only invariants.yaml + templates + the substrate module.
This demonstrates the N-agent expansion property: adding LegalAgent
or ItOpsAgent next would follow the same shape.

### Total skill count after v0.8

| Role | Reference skills |
|---|---|
| ChiefOfStaff | 11 |
| KnowledgeBase | 7 |
| SystemSentinel | 7 |
| AnalystJudge | 8 |
| BusinessDevelopment | 6 |
| WritingSupport | 17 (incl. coaching subsystem) |
| **Finance (new)** | **7** |
| Shared (cross-role) | 2 |
| **Total** | **65** |

## [0.7.0] — 2026-05-24

Three foundational pieces that complete the "operator gets
HermesAgency running with their real data" story.

### Added — Gmail API integration

- **`_framework/integrations/gmail.py`** — same pattern as
  `google_drive` + `google_calendar`. Lazy-imported runtime
  client, profile-local OAuth credentials, three scope presets
  (`readonly` / `send` / `modify`).
- Public API: `list_new_messages`, `list_message_ids`,
  `get_message`, `send_message`, `create_draft`, `modify_labels`,
  `archive_message`, `mark_read`.
- MIME builder handles text-only, text+html alternative, and
  attachments-mixed. Threading via `In-Reply-To` + `References`
  headers or Gmail's `threadId`.
- `setup_interactive()` walks the OAuth consent flow + stores
  the refresh token at `profiles/<id>/credentials/gmail_token.json`.

### Added — Tier 2 interactive wizard flow

- **`_framework/ops/init/tier2_flow.py`** — the substantive
  Tier 2 implementation (Tier 1 → manifest skeleton; Tier 2 →
  integrations + ingest + ingress; Tier 3 → deep agency-vault
  interview).
- Walks the operator through Gmail/Calendar/Drive OAuth setup
  (each skippable — deferred steps land in deployment.yaml as
  `tier2.deferred_steps` so `agency status` surfaces them).
- Captures ingest sources (RSS / atom / webhook).
- Captures digest cadence (morning briefing / triage batches /
  weekly review DOW+time).
- Captures ingress channels (email / chat-tab / Signal / Slack /
  OpenWebUI).
- Persists everything to `deployment.yaml::ingress` +
  `tier2.*` sections.
- Wired into the wizard so `agency init --tier 2` (or `--tier 3`)
  runs it after Tier 1 base provisioning.

### Added — v7 migration tool

- **`_framework/migration/v7_learning.py`** — read v7's
  `loriah.db::learning_rules` + translate to HermesAgency's
  `learning.db` schema. Operator-controlled (plan then apply),
  traceable, idempotent, journaled.
- **Plan mode** (`agency migrate v7 plan`) — reads source, classifies
  each row's disposition (`migrate-fresh` / `already-present` /
  `skip-superseded` / `skip-empty` / `skip-dedup`), prints summary
  + sample of 5 to migrate. No writes.
- **Apply mode** (`agency migrate v7 apply`) — runs each
  `migrate-fresh` row through `capture_correction()` so embeddings
  get generated freshly, then backfills the v7 id so audit
  references stay intact. Idempotent: re-runs are safe.
- Journal at `_health/migration-journal.jsonl` records per-row
  outcome with v7 id, timestamp, preview, disposition, error (if
  any).
- **Live-verified against AJ's real v7 db** (304 rules, 270 ready
  to migrate, 34 correctly skipped as superseded/empty).

### CLI additions

- `agency migrate v7 [plan|apply] --from /path/to/loriah.db`
  (defaults to `~/.hermes/context/loriah/Admin/loriah.db`)
- Existing Tier 2/3 wizard flows already auto-invoke the new
  interactive paths

### Tests

142 passing (129 from v0.6 + 13 new):
- 9 Gmail tests (configured-state, addr parsing, MIME builder
  text-only / html / attachment / threading, scope presets,
  require-configured guard)
- 4 Tier 2 flow tests (defaults, manifest persistence, Gmail-setup-
  when-yes, ingest-source capture)
- 6 v7 migration tests (plan dispositions, apply correctness,
  idempotency, journal, missing source, already-present-after-apply)

Framework self-audit: 0 blocking, 0 warnings.

### What this enables

After v0.7, an operator running `agency init --tier 3` gets:
- A manifest + 3 scaffolded profiles (Tier 1)
- Gmail/Calendar/Drive OAuth wired (Tier 2, if they say yes)
- Ingest sources + digest cadence + ingress channels set (Tier 2)
- Goals.md / Values.md / Personal.md / Work.md / Clients.md drafted
  from interview (Tier 3)
- Per-agent personalization applied to SOUL.md (Tier 3)

Then: `agency migrate v7 plan` shows what migrates from their prior
deployment; `agency migrate v7 apply` writes it. Their 270+ learning
rules land in HermesAgency with v7 ids preserved for cross-system
audit trails.

That's the full "get running with my real data" flow.

## [0.6.0] — 2026-05-24

Two core CoS functions AJ called out as missing: a **time-use
analyzer** (calendar reality vs Goals.md stated priorities) and a
**SMART goal coach** (Q&A → drafted goals + interim milestones,
round-tripped to Goals.md).

### Added — _framework/goals/

- **`goals_md.py`** — round-trip parsing + structured editing of
  `Goals.md`. `read_goals()` returns `ParsedGoals` with sections
  + a structured `annual_goals` list (each goal + its interim
  milestones as sub-bullets). `add_annual_goal()`,
  `replace_annual_goal()`, `add_active_project()` preserve every
  section the operator hasn't asked to touch.
- **`smart.py`** — heuristic SMART criteria checker. Scores
  Specific / Measurable / Relevant / Time-bound (Achievable is
  operator-asserted — depends on resources). Returns a
  `SmartVerdict` with per-dimension pass/fail + specific
  follow-up questions for any failing dimension.
  Renders into a readable block.

### Added — two CoS skills

- **`time-use-analyzer`** — pulls calendar events + kanban completions
  for a window, maps each to `Goals.md::ANNUAL_GOALS` /
  `Active strategic projects` / unmapped (free), produces a drift
  report: hours per goal, stated-priority-vs-actual gap, protected-
  time check (`Personal.md::WORK_LIFE_BOUNDARIES`), unstructured-time
  pockets, recommended re-allocations.
- **`smart-goal-coach`** — Q&A coaching to refine vague aspirations
  into SMART goals. Runs `smart_check`, identifies missing dimensions,
  asks specific follow-up questions ("By when? What specifically?"),
  drafts the goal in SMART form, proposes interim milestones, and on
  operator confirmation writes to `Goals.md` via the goals module.

### Added — `agency goals` CLI

- `agency goals show` — display current Goals.md
- `agency goals smart-check --text "..."` — runs the SMART checker,
  prints per-dimension verdict + follow-up questions
- `agency goals add --text "..." [--interim ... --interim ...] [--smart]`
  — adds an annual goal; `--smart` refuses if SMART fails
- `agency goals replace --index N --text "..."` — replace existing
- `agency goals add-project --text "..."` — append to Active projects

### Tests

129 passing (119 from v0.5 + 10 new):
- 4 SMART tests (vague fail, clear pass, binary outcomes, missing-T
  surfaces specific question)
- 6 Goals.md tests (read empty, parse sections w/ interim, add
  appends, replace works, replace OOB raises, write-back preserves
  untouched sections)

Framework self-audit: 0 blocking, 0 warnings.

### How the two new functions compose

`smart-goal-coach` *defines* what matters. `time-use-analyzer`
*measures* whether the calendar matches. Together they close the
intent→reality loop:

  vague aspiration  →  SMART goal in Goals.md  →  calendar drift report
                            ↑                            ↓
                            └─ refine the goal when reality diverges
                               (or accept the goal isn't really
                               priority and re-rank in Goals.md)

The CoS's weekly review will now include both: "here's where time
went; here's how Goals.md says it should have gone; here's the
delta + what to do about it."

## [0.5.0] — 2026-05-24

Three AJ directives, each addressed:

  1. "Is obligation-board needed if you have kanban?" → No.
     Refactored to `obligation-extractor` (a sourcing skill that
     creates kanban tasks); the tracking surface is just kanban
     with `tenant=obligation`.
  2. "hardware-research should be generic shopping-research" →
     Renamed + rewritten to handle any purchase category with a
     specifics interview (min/max price, constraints, use-case)
     before searching.
  3. "Writing skills should accept examples + audience + purpose
     and produce a fast first draft, then iterate" → Built the
     prototyping flywheel as a first-class subsystem.

### Added — Prototyping flywheel

- **`_framework/prototyping/`** module:
  - `ingest.py` — examples from URL / file (.txt/.md/.docx/.pdf) /
    raw text → normalized text. HTML stripper, format dispatcher,
    swappable HTTP fetcher (tests pass a stub).
  - `style.py` — `derive_style()` returns a `StyleSignature` with
    sentence rhythm, paragraph density, register classification,
    structural signals (headings/lists/quotes/code), distinctive
    phrases, formatting notes. Renders into a markdown block the
    LLM uses as drafting context.
  - `iteration.py` — `prototypes.db` schema + CRUD:
    `start_prototype` / `record_iteration` / `get_prototype` /
    `list_prototypes` / `mark_shipped` / `convergence_diagnostic`.
    The diagnostic flags 5+ rounds without shipping, feedback not
    shortening, or single-reviewer blind spots.
- **`prototype-from-example`** shared skill — cross-role
  (Writing primary, also CoS/BD/Analyst). The flywheel entry
  point.
- **`iteration-tracker`** shared skill — generic feedback-round
  recorder + stuck-loop diagnostic for any artifact.

### Updated — Existing skills now reference the flywheel

- `newsletter-drafting` — invokes prototyping with prior issues
  + audience + purpose; iteration recorded
- `workbook-drafting` — prior workbooks as examples; first-pass
  structure quickly
- `draft-composer` (CoS) — example-driven option when "match
  this thread's voice" applies
- `opportunistic-outreach` (BD) — prior successful outreaches as
  examples for same-shape pitches

### Refactored

- **obligation-board → obligation-extractor**: the extractor pulls
  commitments from messages and creates kanban tasks with the new
  `tenant=obligation`. Kanban *is* the tracking surface (no
  separate obligation-board DB or UI needed).
- **hardware-research → shopping-research**: works for any purchase
  category. Adds the specifics interview step (more detail is
  better; ask min/max + constraints + use-case) before searching
  multi-vendor sources.
- **kanban_tenants** updated: `hardware` → `shopping`, added
  `prototype` and `obligation`.

### Tests

119 passing (107 from v0.4 + 12 new prototyping tests):
- 5 ingest tests (raw / file / HTTP via stub / HTML stripping /
  batch error isolation)
- 4 style tests (short-sentence detection, structural signals,
  serialization, prompt-block rendering)
- 3 iteration tests (lifecycle, convergence-stuck detection,
  convergence-healthy detection)

Framework self-audit: 0 blocking, 0 warnings.

### Decisions logged

- Style signature is *coarse* by design (rhythm, structure,
  register, top phrases). The fine work — "does this draft sound
  like the examples?" — is the LLM's job at draft time, given
  the signature *and* the raw example texts as context. Better
  than dumping the texts in with no structured hints.
- HTTP fetcher is pluggable (operators who need readability lib /
  JS rendering / paywall handling swap by passing a `fetcher`
  callable). Default is urllib + simple tag-stripper.
- Stuck-loop diagnostic uses three signals (round count without
  ship, feedback length trend, reviewer diversity). Need ≥2 of
  3 to fire — single signal could be noise.

## [0.4.0] — 2026-05-24

Addresses two direct AJ questions:
  1. "Does the setup interview give a chance to name agents,
     choose pronouns, customize personality?" → now yes, in Tier 3.
  2. "Did you draw on actual v7 skills for the manuscript creation
     centerpiece?" → was a real gap. Now closed with the coaching
     subsystem + 6 new Writing skills + 3 new scripts.

### Added — Per-agent personalization in Tier 3

- `_framework/ops/init/agent_personalization.py` — per-agent
  interview captures display name (functional id like `cos`, or
  human-named like `Maya`), pronouns (she / he / they / it / none),
  personality sketch (2-3 sentences).
- Personalization appends as a `## Personalization` block to each
  profile's `SOUL.md` after the role-default content. Skipping
  all three options leaves the default SOUL.md unchanged.
- Tier 3 wizard now loops profiles by default; CoS gets a focused
  voice-notes question afterward for outbound-voice specifics.

### Added — Coaching subsystem (the manuscript creation centerpiece)

Generalized from v7's `book_coaching.db` workflow ("Scribe Method").

- **`_framework/coaching/`** with `coaching.db`:
  - `users` (email PK), `projects` (renamed from "books" — works for
    theses / screenplays / white papers), `phases`,
    `qa_history` (with `answer_source = voice|typed|imported`),
    `deliverables`, `ingested_files` (sha256 dedup)
- **6 new Writing skills**:
  - `coaching-method` — the central Q&A coaching workflow (the
    skill formerly under-covered in `book-coaching`)
  - `structural-edit`, `voice-edit`, `polish-edit` — three
    sequential editor lenses (each scores 0.0-1.0, target ≥0.90
    to pass to the next). Ported from v7's `scribe-*-editor`
    triple.
  - `manuscript-ingest` — capture mechanism for .docx / .pdf / .txt
    / voice memo attachments with sha256 dedup
  - `voice-memo-transcribe` — faster-whisper STT with per-segment
    confidence flags
- **3 new script templates**:
  - `coach-method.py` — the no_agent cron template (self-contained
    deterministic flow; LLM as tool not boss)
  - `ingest-attachments.py` — mechanical extraction layer
  - `transcribe-voice-memo.py` — STT with confidence reporting

### Added — The no_agent cron pattern (DEVELOPMENT_PLAYBOOK §5.6)

V7's critical architectural lesson, now documented as a first-class
framework pattern. Workflows where LLM "creativity" would corrupt
state (book coaching progress, financial records, anything appended
to long-running tables) declare `no_agent: true` in jobs.json.
The cron runs a self-contained script that owns DB + side-effect
authority; inference is called as a tool for content generation
only. Reference example: `_framework/coaching/` + `coach-method.py`.

### Added — Misc v7 skills (3 new)

- **`push-notify`** (CoS) — desktop notifications for
  important-AND-urgent items, with rate-limit guard
- **`obligation-board`** (CoS) — tracks {{OWNER}}'s own commitments
  (different from kanban, which is agency-owned work); surfaces
  overdue with escalating friction
- **`hardware-research`** (Analyst) — market research + price
  comparison + recommendation for hardware purchase decisions

### Tests

107 passing (96 from v0.3 + 11 new):
- 5 agent-personalization tests (personas, pronoun handling,
  appendix writing, skip-when-default, Tier 3 integration)
- 6 coaching tests (user upsert, project lifecycle, Q&A open/
  answered, ingested-file dedup, deliverables, paused-project
  exclusion)

Framework self-audit: 0 blocking, 0 warnings.

### Honest accounting

In v0.3 I built `book-coaching` / `manuscript-review` /
`workbook-drafting` / etc. for Writing — covering the STANDARDS-
file description but missing the actual centerpiece (the
phase-driven Q&A coaching workflow with attachment ingestion and
the three-editor pipeline). This release closes that gap.

The no_agent cron pattern is the deeper architectural lesson — I'd
missed it entirely. Without it, the coaching pipeline would have
been rebuilt with the same vulnerability as v7's earlier version
(LLM with DB write authority becoming "creative" about state).

## [0.3.0] — 2026-05-24

Coverage release — "better to have skills available that aren't
needed than skills needed that aren't available." All 36 starter
skills declared in `deployment.yaml.template` now ship as real
reference SKILL.md files. New substrate modules (CRM, per-subject
state, Google Calendar integration) support them. Cron script
templates cover the v7 operational shape.

### Added — Starter skills (35 new reference files)

- **Chief of Staff (9 total)**: + owner-channels-ingress,
  send-orchestrator, kanban-orchestrator, calendar-manager,
  morning-briefing, weekly-review, delegate-via-kanban,
  pipeline-watchdog
- **KnowledgeBase (7 total)**: + ip-curator,
  methodology-application-check, prior-decision-search,
  meeting-evaluator, quality-auditor, kanban-verdict-publisher
- **SystemSentinel (7 total)**: + learning-monitor, drift-monitor,
  heartbeat-watch, playbook-audit, event-rollup, compliance-report
- **AnalystJudge (7 total)**: + dossier-builder, research,
  prompt-injection-defense, learning-curation,
  verifier-criteria-author, graduation-check
- **BusinessDevelopment (6 total)**: + opportunistic-outreach,
  journalist-relationship, podcast-host-relationship, crm-sync,
  weekly-opportunity-scan
- **WritingSupport (5 total)**: + manuscript-review,
  workbook-drafting, newsletter-drafting, multi-author-state

Each skill carries real frontmatter (autonomy block, action classes,
voice tags), supervised-learning wire, typed verifier criteria, and
self-check. They're starting points an operator copies + customizes,
not stubs that say TODO.

### Added — Substrate modules

- **`_framework/crm/`** — Generic CRM (contacts, leads, sent_threads,
  reply_log) with the 4-priority reply matcher from v7
  (thread_id → email → domain → unmatched). Domain-specific fields
  (NCES ids etc.) live in JSON `metadata` columns, keeping the
  schema reusable across very different agencies.
- **`_framework/per_subject_state/`** — One pattern for per-author
  state (Writing), per-coach state (KB), per-journalist /
  per-podcast state (BD), per-subject dossier state (Analyst).
  Filesystem-namespaced with hard guards against cross-subject leak.
- **`_framework/integrations/google_calendar.py`** — Same pattern as
  `google_drive`: lazy-imported client, profile-local credentials,
  list/create/update/delete + `find_conflicts()`.

### Added — Script templates (10 new starters)

- `pipeline-watchdog` — CoS pipeline observability
- `triage-batch` — render queued items into batched summaries
- `archive-enforcer` — hard archive-rule enforcement from corpus
- `classification-enforcer` — hard classification-rule enforcement
- `find-candidates` — BD signal-driven prospect identification
- `outreach-tracker` — verify delivery + schedule follow-ups
- `follow-up-generator` — draft follow-ups for stalled leads
- `poll-inbox` — fetch new mail + route through reply-matcher
- `system-health` — platform sanity check (DB integrity, disk, dirs)
- `hardware-watch` — local hardware vitals

Each follows the playbook (shebang + try/except + event emission +
heartbeat) and is audit-clean by construction.

### Tests

96 passing (85 from v0.2 + 11 new CRM/state):
- 8 CRM tests (lead/contact/alternate-emails, 4-priority reply
  matcher across all priorities, log_reply)
- 3 per-subject-state tests (namespace guard, lifecycle, isolation)

### Decisions logged

- Generic CRM schema deliberately keeps domain-specific fields in
  JSON `metadata` columns rather than typed schema. Trade-off:
  weaker typing, far more reusable across agency types.
- `per_subject_state` uses filesystem (markdown + JSON) rather than
  a DB. Trade-off: less queryable, more git-friendly + human-readable
  + per-subject grep-able.
- Script templates ship a `TRANSPORT BLOCK` comment marker for
  mail-backend wiring rather than picking a default (Himalaya vs
  Gmail OAuth vs IMAP) — operator chooses.

## [0.2.0] — 2026-05-24

Closes the gap between "framework skeleton" and "framework that
actually operates against Hermes." All five framework-level fixes
identified in the v0.1 retrospective are landed, plus the v7
patterns AJ called out as still needed.

### Added

- **standards.md.template refactor** — all 6 role templates now match
  the v7 richer structure (Job Description, Owned Deliverables with
  skill references, What to Include/NOT Include Me On, How Best to
  Collaborate, Resolving Conflict).
- **Agency-vault layer** — `~/.agency/agency-vault/` with templates
  for Goals.md (the most important doc the agency reads),
  Values.md, Personal.md, Work.md, Clients.md.
- **Tier 3 deep interview** — `agency init --tier 3` runs a
  substantive interview generating first drafts of all five
  agency-vault docs + CoS voice notes.
- **State-vault layer** — `~/.agency/state-vault/` with
  `operational-state.md` and `conversation-journal.md` initialized
  by Tier 3. `_framework/state/` provides read/write helpers and
  section-aware append with quarterly prune.
- **Hermes kanban integration shim** — `_framework/kanban/` uses
  Hermes' real `kanban_db` (no duplication). Idempotent ALTER adds
  `task_links.link_type` (default `blocks` preserves Hermes' prior
  behavior). Adds `tracks` semantics + `claim_task_for_skill` +
  `complete_with_verifier`.
- **Hermes cron integration** — `_framework/cron/` syncs per-profile
  `cron/jobs.json` into Hermes' canonical `~/.hermes/cron/jobs.json`,
  tagging framework-owned jobs so operator-authored jobs are
  preserved across syncs.
- **Hermes injection patches** — `_framework/hermes_patches/` with
  applicable `skill_load_injection` patch for Hermes'
  `agent/skill_commands.py::_build_skill_message`. Idempotent,
  marker-detected, backed up, journaled. Without this, captured
  learning rules don't reach the model — the critical wire.
- **Heartbeats** — `_framework/heartbeats/` with `beat(component)` +
  `stale_components()` against
  `invariants.yaml::expected_intervals_seconds`.
- **Reference SKILL.md per role** — substantive working examples
  (`draft-composer`, `ip-alignment-check`, `heartbeat-emit`,
  `red-team`, `prospect-research`, `book-coaching`).
- **Google Drive integration** — `_framework/integrations/google_drive.py`
  with `upload_and_share` and interactive OAuth setup. Profile-local
  credentials. Optional Python deps.
- **New CLI surface** — `agency hermes-patches`, `agency cron`,
  `agency state`, `agency heartbeat`, `agency integrations`.

### Tests

85 passing (65 from v0.1 + 20 new).

### Removed / out-of-scope

- delegations.md tracker — kanban handles it.
- n8n integration — explicitly out of scope.
- Pre-v7 intercom pattern — kanban does the job.

### Still deferred to v0.3+

- T2 wizard interactive flow (OAuth + ingress detail)
- Email-OTP auth on remote dashboard
- Auto-reapply Hermes patches on `pip install --upgrade` hook
- Cost/token attribution per skill, synthetic edge-case battery,
  mesh layer, multi-machine, owner content migration, PyPI publishing
- Google Calendar / Gmail-API / Signal / Slack integrations

## [0.1.0] — 2026-05-23

First public release. All acceptance criteria from §12.1 of
`HERMES_AGENCY_V0.1_SPEC.md` met.

### Added

- **Framework skeleton** (Week 1): `_framework/` package, brand-
  agnostic path constants, single-source-of-truth invariants
  (`_framework/invariants.yaml`), deployment.yaml validator with 10
  error/warn rules.
- **Learning subsystem — the spine** (Week 2): seven-step learning
  loop end-to-end. `learning_rules`, `firings`, `recapture_events`,
  `recapture_denylist` tables; pluggable `Embedder` interface with
  `HashEmbedder` default; three-axis tagging (skill / role / voice);
  inline recapture detection at capture-time; weekly compliance
  report.
- **Autonomy + Verifier + Send-guard** (Week 3): L1-L5 ladder with
  three-input promotion gate (track record + audit-strict + learning
  fidelity); 10 typed verifier criterion types; outbound mail
  validation with access list, hard ceilings, hard-rule validators.
- **Sentinel + Audit** (Week 4): read-only Sentinel role with
  events.db + cron monitors (learning-monitor, drift-monitor,
  heartbeat-watch, event-rollup, compliance-report, playbook-audit);
  7-category audit-alignment engine with 20+ rules; `--strict` flag
  for graduation-gate use; `framework-vendor-leak` rule enforcing
  vendor-neutrality.
- **Six role templates** (Week 5): each role ships substantive
  `SOUL.md.template` (1-2 page persona) and `standards.md.template`
  (operational quality floor) — chief-of-staff, knowledge-base,
  system-sentinel, analyst-judge, business-development, writing-
  support. Scaffolds: `scaffold-skill`, `scaffold-script`,
  `scaffold-profile`.
- **Wizard + CLI + Control panel + Docs** (Week 6): three-tier
  `agency init` wizard (T1 fully working in v0.1); 11-command
  `agency` CLI (status / init / manifest-validate / audit / capture
  / learn / promote / demote / events / upgrade / panel); aiohttp
  read-only control panel at localhost:9118; docs for ARCHITECTURE,
  LEARNING_LOOP, AUTONOMY, SENTINEL, ROLES, DEPLOYMENT,
  PATCHES_TO_HERMES; `DEVELOPMENT_PLAYBOOK.md` v2.0.0 (generic,
  framework-distributable).

### Tested

65 tests passing across 10 categories:
- 10 manifest validator tests
- 12 learning-spine tests (capture, inject, fire, recapture,
  compliance report)
- 9 autonomy tests (clean-runs, failures, three-input gate scenarios)
- 7 verifier tests (all 10 criterion types exercised)
- 7 send-guard tests (allow / hold / deny / firings on override)
- 12 audit tests (7 categories + framework self-audit)
- 3 wizard tests
- 3 control-panel tests
- 1 end-to-end smoke test exercising §12.1 acceptance bar
- 1 events.db append/recent test

### Out of scope (deferred to v0.2+)

- Owner content migration (per §13 migration plan)
- Cost/token attribution per skill
- Multi-machine deployment
- Quarterly deep semantic audit pass
- Tier 2/3 wizard interactive flows (OAuth, exemplar capture, IP import)
- Control panel interactive controls (pause/resume/run)
- Email-OTP authentication for remote dashboards
- Synthetic edge-case battery
- Mesh layer for cross-deployment agent collaboration
- Auto-reapply hook for Hermes upstream patches
