# HermesAgency: The Agent Team Designed for Solopreneurs & Small Businesses

### Powerful Autonomous Team. Continuous Context Learning. Complete Privacy & Data Control.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Hermes engine](https://img.shields.io/badge/plugin%20for-Hermes%20Agent-purple)](https://github.com/NousResearch/hermes-agent)

HermesAgency is a multi-agent framework built as a plugin to [NousResearch's](https://github.com/NousResearch/hermes-agent) powerful Hermes agentic engine. Designed for and by small-business owners, HermesAgency pulls together the suite of capabilities every small business wants and needs but typically can't afford. It's where the powerful, always-working aspects of *technological intelligences* (the agents) collaborate with the ingenuity and creativity of *biological intelligences* (the humans). Together, with a **7-part continuous learning framework** designed from the ground up to rapidly expand the agents' understanding of the human's goals and values, HermesAgency gives business leaders access to the advantages of companies many times their size and revenue — without sacrificing the privacy and ownership of your data and intellectual property, and without getting locked into big-tech ecosystems. The owner's declared goals and values (in `Goals.md`, `Values.md`, and the other agency-level context docs) are always part of the background the agency operates in — present every turn, never the foreground, never absent.

> By [AJ Crabill](https://ajcrabill.com) — AI Developer for [Good Ancestor](https://www.GoodAncestor.com). HermesAgency is the 9th version of a personal AI chief-of-staff project that's been running, breaking, and getting rewritten on and off for years — see spec §0.5 for the full lineage (VPS + OpenClaw → Claude Cowork → dCoS → Hermes-rebased → DeepSeek → multi-agent → standalone fork → proper plugin). The current architecture is hard-won simplicity.

## What HermesAgency does for you

A small-business owner wears every hat. HermesAgency runs a team of agents that quietly takes the most repetitive, easily-lost, and easily-dropped work off your plate — without you having to surrender your data, your relationships, or your judgment. Here's a sample of what your agency can do:

### Win new business

- **Spot referral opportunities you'd otherwise miss** — surfaces the warm handoffs your existing clients casually mention in email and turns them into drafts ready for your review
- **Find new prospects who look like your best clients** — analyzes the businesses you already serve to identify common traits, industries, and geographies worth targeting
- **Nurture your "someday" pipeline on autopilot** — keeps the slow-burn leads warm with timely nudges so you stop losing deals to silence
- **Scan your industry for moments worth your voice** — newsworthy stories, viral threads, conferences — surfaced as opportunities to jump in with thought leadership

### Stay on top of communications

- **Draft email and writing in your voice** — learns from samples of your prior writing; subsequent drafts sound like *you*, not like a chatbot
- **Triage your inbox** — separates what actually needs your attention from what doesn't, with a daily summary instead of constant interruption
- **Turn voice memos into written drafts** — record a voice note while driving; get back a polished blog post, client email, or memo ready to edit
- **Track conversations you've started and need to follow up on** — the agency keeps a thread-aware view of who you're waiting on and who's waiting on you, so deals don't die in silence

### Run your operations

- **Manage your calendar end-to-end** — finds time, batches similar meetings, avoids double-booking, and flags conflicts before they bite
- **Keep tasks moving across your team** — kanban with explicit dependencies; you see what's blocked, what's late, and what's actually shipping
- **Surface emails that still need a reply** — nothing falls off the bottom of the inbox because it scrolled out of view
- **Stay on top of invoices, expenses, and late-paying clients** — the agency tracks money in, money out, and the receivables you've been meaning to chase
- **Keep your operational documentation current** — when something changes, the agents update the relevant docs so you stop running into stale process notes
- **Notify you only when a human is actually needed** — push alerts are rare and meaningful, not constant noise

### Plan your next quarter

The agency operates with your declared goals and values always part of its background context. Update `Goals.md`, and the work shifts to track. HermesAgency uses a **three-layer strategic-planning model** (Outcomes → Interim Goals → Initiatives, all SMART) so the work the agency does this week is structurally traceable back to the outcomes you've declared. See [`docs/StrategicPlanning.md`](./docs/StrategicPlanning.md) for the framework.

- **Coach you toward SMART goals you'll actually measure** — interactive Q&A that turns vague intentions into Outcomes, Interim Goals, and Initiatives with metrics attached at each layer
- **Compare your calendar to your stated goals** — see where your time is leaking and where the gap is between what you say matters and how you spent the week
- **Three concrete actions every week** — weekly brainstorm proposing specific moves based on what's happening in your business *right now*, not generic advice
- **Ask the testability question** — every week the agency asks: *are these inputs (Initiatives) moving the outputs (Interim Goals), and are the outputs moving the outcomes (Goals)?* The answer is measurable, not a vibes check

---

## Why this exists

Every large platform is rolling out the same feature set: AI assistants, multi-agent workflows, persistent memory, learning from corrections, integrated calendaring and email. The capability gap that used to favor enterprises is collapsing — fast. **A small business without these tools is at a real disadvantage against competitors that have them.**

But the big-platform versions of these features come at a price:

- **Ecosystem lock-in** — your obligations, contacts, IP, and drafting workflows live inside a platform; switching means abandoning your institutional memory
- **Data exfiltration as the price of admission** — your IP, client information, private deliberations, unfinished ideas, strategic thinking all get uploaded
- **Per-seat economics that scale with team size, not with the value the features unlock**

HermesAgency gives small-business owners the same capabilities — **continuous learning, multi-agent workflows, integrated communication, autonomy-graded delegation** — without trading the data, IP, or ideas that make their business distinct. The architectural commitments that make this true:

- **Runs on your hardware.** Hermes Agent + HermesAgency operate on your machine; the agency layer has no cloud dependency. State lives in `~/.hermes/agency-state/` on *your* filesystem.
- **Vendor-neutral inference.** Pick your model. Mix providers. Run local-only with Ollama / Qwen / Gemma for zero data egress. The framework names no vendor (enforced by an audit rule); providers are configuration, not code.
- **MIT-licensed, open source.** Full code visibility. No SaaS pricing curve. No telemetry. No phone-home.
- **Your IP stays yours.** Corrections, learning rules, vault documents, drafts — all in your filesystem, under paths you control. The framework reads from them but never copies them anywhere.

The competitive thesis is straightforward: **the small business that masters their own AI agency wins.** HermesAgency is the path that doesn't require trading ownership of your IP for the capability.

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

1. **Supervised learning loop** — captures every correction you give, propagates it to every relevant skill across the agency, and tells you when the loop breaks (so you stop repeating yourself). Your declared goals and values (in `Goals.md`, `Values.md`, and the other agency-level context docs) are always part of the background context the agency operates in — never the foreground, never absent
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
