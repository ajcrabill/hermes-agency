# Changelog

All notable changes to HermesAgency are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Major bumps signal breaking deployment changes (manifest schema, on-disk
layout). Minor bumps signal new starter skills, new audit rules, or new
roles. Patch bumps are fixes only.

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
