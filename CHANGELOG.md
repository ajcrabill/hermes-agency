# Changelog

All notable changes to HermesAgency are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Major bumps signal breaking deployment changes (manifest schema, on-disk
layout). Minor bumps signal new starter skills, new audit rules, or new
roles. Patch bumps are fixes only.

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
