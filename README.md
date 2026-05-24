# HermesAgency

**A Hermes plugin that adds 7 reliability systems for small-agency owners who refuse to re-teach their AI ten times.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Hermes engine](https://img.shields.io/badge/plugin%20for-Hermes%20Agent-purple)](https://github.com/NousResearch/hermes-agent)

---

## The 4-step install

```bash
# 1. Install Hermes (NousResearch's agent engine — the runtime)
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.zshrc   # or ~/.bashrc — reload to pick up the `hermes` binary

# 2. Install HermesAgency (the plugin — adds the 7 reliability systems)
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash

# 3. Migrate v7 data (skip if you don't have a prior install)
agency migrate v7 apply --from ~/.hermes-v7-backup --profile loriah

# 4. Use it
hermes
```

That's the whole install. Step 2 registers HermesAgency as a Hermes plugin
(symlinked into `~/.hermes/plugins/hermes-agency/`). Hermes discovers it
on next launch and starts calling our lifecycle hooks: learning rules
inject into every turn, the autonomy ladder gates tool calls, the send-guard
intercepts outbound mail, Sentinel observes session boundaries.

Inside `hermes`, run `/agency systems` to confirm all 7 reliability
systems are wired.

---

## What this is

[NousResearch's Hermes engine](https://github.com/NousResearch/hermes-agent)
is the runtime. You run it via `hermes` (interactive), `hermes chat`, or
`hermes run <skill>`. HermesAgency is a **plugin** that makes Hermes more
reliable in 7 specific ways:

1. **Supervised learning loop** — captures every correction you give, propagates it to every relevant skill across the agency, and tells you when the loop breaks (so you stop repeating yourself)
2. **Autonomy ladder (L1–L5)** — agents earn more independence over time, gated on track record + structural compliance + learning fidelity
3. **Verifier** — every skill completion runs through testable criteria before counting as done
4. **System Sentinel** — read-only observer; alarms when something drifts, never firefights
5. **Kanban tracks-link type** — adds a `tracks` relationship to Hermes' kanban so cross-profile dependencies are explicit
6. **Send-guard** — outbound mail gate; nothing leaves the agency without passing this checkpoint
7. **Audit** — weekly alignment check across profiles, skills, scripts, and integration patches

Each system is meant to wire into Hermes' own execution path — not run alongside it. See **`agency hermes-patches systems`** for the honest integration state on your install.

**As of v0.17.0, all 7 reliability systems are Hermes-extending** — wired
via the documented Hermes plugin API (`pre_llm_call`, `pre_tool_call`,
`post_tool_call`, `on_session_start`, `on_session_end` hooks). The text-
anchor patch approach used through v0.16 is deprecated. See
`docs/HERMES_AGENCY_SPEC.md` §1.4 (plugin discipline) and §1.5 (the
7-system table).

## How you use it (after the 4-step install)

```bash
hermes                         # The runtime. HermesAgency invisibly enriches it.

agency hermes-patches systems  # See which of the 7 systems are actually wired
agency status                  # HermesAgency-specific health
agency next                    # actionable next-steps for your specific state
agency capture "..."           # Capture a correction (opens the learning loop)
agency audit                   # Run the alignment audit
agency migrate v7 apply --from <path>  # Pull a prior install's data in
```

There is no `agency chat` for daily use. `agency chat` exists as a diagnostic
when you want to test the prompt composer / rule injection without going
through Hermes — it prints a banner reminding you that the real chat is
always `hermes chat` (or just `hermes`).

---

## Six agent roles, configurable

HermesAgency ships templates for six agent roles (custom roles are first-class — add any number you want):

- **Chief of Staff** — the one face to the owner and the one face to the world. Triages incoming, routes to specialists, owns outbound voice
- **Knowledge Base** — IP corpus curator + alignment-check; weekly industry newsletter
- **System Sentinel** — pure read-only observer; the alarm, not the firefighter
- **Analyst Judge** — adversarial review, dossier-building, research, red-team
- **Business Development** — prospect research, referral hunting, potential-clients pipeline
- **Writing Support** — manuscript coaching, newsletter drafting, thought-leadership scanning
- **Finance** *(optional)* — cash flow, invoicing, revenue attribution

Each role has a persona stub (`SOUL.md`) and a professional-standards floor (`standards.md`). Both are always-injected into skill prompts via the learning loop patch.

---

## Installer reference

The 4-step install above is the recommended path. This section covers
options + alternatives.

### Step 2: bootstrap.sh flags

```bash
# Fresh install (wipes any prior ~/.agency + ~/.agency-venv — does NOT touch Hermes)
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --reset

# Don't run the agency init wizard automatically (you'll run it manually later)
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --no-init

# Don't auto-apply the Hermes patches at end of install
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --no-patches
```

Full flag list: `--target=<dir>`, `--venv=<dir>`, `--ref=<branch>`.

### Step 3: migrate options

```bash
# Plan-only (dry run; nothing written)
agency migrate v7 plan --from ~/.hermes-v7-backup --profile loriah

# Apply — the directory mode (full migration: corpus + SOULs + standards + vault MDs + legacy DBs)
agency migrate v7 apply --from ~/.hermes-v7-backup --profile loriah

# Legacy mode: --from points at a loriah.db file (learning corpus only)
agency migrate v7 apply --from ~/.hermes-v7-backup/.hermes/context/loriah/Admin/loriah.db
```

### Manual install (no curl-pipe)

```bash
# Step 1: install Hermes per NousResearch's docs (link above)

# Step 2: clone + install HermesAgency
git clone https://github.com/ajcrabill/hermes-agency ~/HermesAgency
cd ~/HermesAgency
bash bootstrap.sh            # same flags as the curl-pipe version
```

### Tier choices

`agency init` (called by bootstrap.sh) defaults to **Tier 1** (5-10 min, sensible defaults). To pick a deeper tier:

```bash
agency init --tier 2 --force   # T2 (15-30 min): OAuth + ingress + ingest sources
agency init --tier 3 --force   # T3 (45-60 min): deep interview, exemplar capture
```

### Starting over

```bash
agency reset                       # wipe ~/.agency (confirm with 'wipe')
agency reset --include-venv -y     # also wipe ~/.agency-venv, skip prompt
```

Note: `agency reset` does NOT touch your Hermes install. To reset Hermes,
use Hermes' own tooling (`hermes update`, etc.).

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for full setup details.

---

## Architecture at a glance

```
                    OWNER CORRECTION
                          │
                          ▼
            ┌─────────────────────────────┐
            │     LEARNING SUBSYSTEM      │
            │  capture → tag → inject →   │
            │       record → recapture    │
            └─────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ AUTONOMY │ │ VERIFIER │ │  KANBAN  │
        │  LADDER  │ │   SEAM   │ │   SEAM   │
        └──────────┘ └──────────┘ └──────────┘
              │
              ▼
        ┌──────────┐
        │ SENTINEL │  watches everything; mutates nothing
        └──────────┘
```

Full architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## The six default roles

| Role | Identity | Sends mail? |
|---|---|---|
| **ChiefOfStaffAgent** | Owner's interface, top-level coordinator | **Yes — the only outbound mail surface** |
| **KnowledgeBaseAgent** | Classify, organize, retrieve, validate against agency IP | No — verdicts only, work routed via kanban |
| **SystemSentinelAgent** | Pure observability + audit; no action authority | No — read-only by design |
| **AnalystJudgeAgent** | Adversarial review, dossier, research, curation | No — internal only |
| **BusinessDevelopmentAgent** | Lead-gen, news-driven outreach, journalist/podcast relationships | No — drafts handed to CoS for review + send |
| **WritingSupportAgent** | Author coaching (multi-author), workbooks, newsletter | No — author correspondence flows through CoS |

Detail in [`docs/ROLES.md`](docs/ROLES.md). Adding new roles (e.g. `FinanceAgent`) is a deployment-level config change — no framework PR required.

---

## Status

**v0.1 is under active development.** This README and the contents of this repo evolve as the build progresses. The build target is the acceptance bar in §12.1 of `HERMES_AGENCY_V0.1_SPEC.md`.

See [`CHANGELOG.md`](CHANGELOG.md) for current state.

---

## License

[MIT](LICENSE) — copy, modify, distribute. The framework is yours; your deployment is yours.

---

## Acknowledgements

HermesAgency builds on:

- [NousResearch Hermes](https://github.com/NousResearch/hermes-agent) — the agent engine underneath
- [agent-core](https://github.com/ajcrabill/agent-core) — many ideas borrowed (three-tier setup wizard, goal-directed operation, markdown projection, vendor-neutrality)
- [dCoS](https://github.com/ajcrabill/dCoS) — early thinking on the deep-interview setup pattern

Patterns from both are explicitly credited in `docs/ARCHITECTURE.md` Appendix A.
