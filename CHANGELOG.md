# Changelog

All notable changes to HermesAgency are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Major bumps signal breaking deployment changes (manifest schema, on-disk
layout). Minor bumps signal new starter skills, new audit rules, or new
roles. Patch bumps are fixes only.

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
