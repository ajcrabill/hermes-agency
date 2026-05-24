# Changelog

All notable changes to HermesAgency are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Major bumps signal breaking deployment changes (manifest schema, on-disk
layout). Minor bumps signal new starter skills, new audit rules, or new
roles. Patch bumps are fixes only.

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
