# HermesAgency

**A Hermes plugin that adds 7 reliability systems for small-agency owners who refuse to re-teach their AI ten times.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Hermes engine](https://img.shields.io/badge/plugin%20for-Hermes%20Agent-purple)](https://github.com/NousResearch/hermes-agent)

> **Install in one line** (Python 3.11+, git):
> ```
> curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash
> ```
> Don't have Hermes installed yet? The installer handles it.

## What this is

[NousResearch's Hermes engine](https://github.com/NousResearch/hermes-agent) is the runtime. You run it via `hermes chat` and `hermes run <skill>`. HermesAgency is a **plugin** that makes Hermes more reliable in 7 specific ways:

1. **Supervised learning loop** — captures every correction you give, propagates it to every relevant skill across the agency, and tells you when the loop breaks (so you stop repeating yourself)
2. **Autonomy ladder (L1–L5)** — agents earn more independence over time, gated on track record + structural compliance + learning fidelity
3. **Verifier** — every skill completion runs through testable criteria before counting as done
4. **System Sentinel** — read-only observer; alarms when something drifts, never firefights
5. **Kanban tracks-link type** — adds a `tracks` relationship to Hermes' kanban so cross-profile dependencies are explicit
6. **Send-guard** — outbound mail gate; nothing leaves the agency without passing this checkpoint
7. **Audit** — weekly alignment check across profiles, skills, scripts, and integration patches

Each system is meant to wire into Hermes' own execution path — not run alongside it. See **`agency hermes-patches systems`** for the honest integration state on your install.

> **Architectural honesty:** As of v0.15.0, the patches for the autonomy gate, verifier, and send-guard are not yet built. Those three systems exist as parallel infrastructure that the framework calls itself, but Hermes doesn't currently consult them during skill execution. Sentinel, kanban-tracks, audit, and the learning loop are Hermes-native. The roadmap to close the gap is in `docs/HERMES_AGENCY_SPEC.md` §13.

## How you use it

```bash
hermes chat                    # The runtime. Always was. Always will be.
                               # HermesAgency invisibly enriches what Hermes does.

agency hermes-patches systems  # See which of the 7 systems are actually wired into Hermes
agency hermes-patches apply    # Wire (or reapply) the patches into your Hermes install
agency status                  # HermesAgency-specific health (loop integrity, audit)
agency next                    # Actionable next-steps for your specific state
agency capture "..."           # Capture a correction (how the learning loop opens)
agency audit                   # Run the alignment audit
```

There is no `agency chat` for daily use. `agency chat-debug` exists as a diagnostic when you want to test the prompt composer / rule injection without going through Hermes — but the real chat is always `hermes chat`.

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

## Quickstart

> Requires Python 3.11+ and git. **You do NOT need Hermes installed first** —
> the wizard's first step detects an existing install or installs Hermes for you.

### One-command install

```bash
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash
```

That single line:

1. Clones HermesAgency to `~/HermesAgency`
2. Creates a venv at `~/.agency-venv`
3. `pip install -e` the framework + extras
4. Runs `agency init` — wizard's **Branch A/B** step asks about Hermes first
   (detect an existing install OR install Hermes fresh for you), then walks
   you through the rest of setup

**Fresh-install (wipes any prior `~/.agency`, `~/.agency-venv`, `~/.hermes`):**

```bash
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --reset
```

**Deeper wipe (also blows away `~/HermesAgency` + the `hermes` symlink):**

```bash
curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash -s -- --reset-deep
```

### After the wizard

```bash
# Activate the venv in future shells (or add to ~/.zshrc)
source ~/.agency-venv/bin/activate

# Wire HermesAgency into Hermes (one-time per Hermes upgrade)
agency hermes-patches apply

# See what's actually wired vs. still parallel infrastructure
agency hermes-patches systems

# Use Hermes — now invisibly enriched by HermesAgency's patches
hermes chat
```

### The supervisory commands

```bash
agency status                # HermesAgency health (loop integrity, audit, Hermes detection)
agency next                  # actionable next-steps for your specific state
agency audit                 # framework self-audit + skill audits
agency hermes-patches apply  # (re)wire the integration patches
agency capture "..."         # capture a correction (the learning loop's first link)
agency panel                 # read-only diagnostic UI at localhost:9118
```

### Diagnostic chat (NOT the daily-use surface)

If `hermes chat` isn't behaving as expected and you want to test the prompt
composer / rule injection in isolation:

```bash
agency chat                  # diagnostic REPL — talks to your provider directly,
                             # bypassing Hermes. Prints a banner reminding you to
                             # use `hermes chat` for normal use.
```

This is for debugging. Once `agency hermes-patches apply` has wired the
integration, `hermes chat` is the surface — it picks up your SOUL, standards,
and learning rules automatically.

### Tier choices

`agency init` defaults to **Tier 1** (5-10 min, sensible defaults). To pick:

```bash
agency init --tier 2         # T2 (15-30 min): OAuth + ingress + ingest sources
agency init --tier 3         # T3 (45-60 min): deep interview, exemplar capture
```

### If you skipped Hermes earlier

```bash
agency init --hermes-only    # just Branch A/B; doesn't touch your manifest
```

### Starting over

```bash
agency reset                       # wipe ~/.agency (confirm with 'wipe')
agency reset --include-hermes      # also wipe ~/.hermes
agency reset --include-venv -y     # also wipe ~/.agency-venv, skip prompt
```

### Manual install (if you don't want to pipe curl into bash)

```bash
git clone https://github.com/ajcrabill/hermes-agency ~/HermesAgency
cd ~/HermesAgency
bash bootstrap.sh            # same flags as the curl-pipe version
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for full setup.

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
