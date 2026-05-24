# HermesAgency

**A multi-agent framework for small-agency owners who refuse to re-teach their AI ten times.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Hermes engine](https://img.shields.io/badge/built%20on-Hermes%20Agent-purple)](https://github.com/NousResearch/hermes-agent)

> **Install in one line** (Python 3.11+, git):
> ```
> curl -fsSL https://raw.githubusercontent.com/ajcrabill/hermes-agency/main/bootstrap.sh | bash
> ```
> Don't have Hermes installed? Don't worry — the wizard installs it for you as Step 0.

HermesAgency is built on top of [NousResearch's Hermes engine](https://github.com/NousResearch/hermes-agent) and gives small-agency owners and operators a working multi-agent agency — Chief of Staff, Knowledge Base, System Sentinel, Analyst Judge, Business Development, Writing Support — with a single architectural promise:

> Every correction the owner gives is captured, tagged, propagated to every relevant agent across the agency, and applied without the owner repeating themselves. The autonomy ladder lets agents earn more independence over time — but only when the learning loop is provably working. The system tells the owner when it isn't.

If you have to re-teach the same correction across contexts, that's a system failure mode here, not an ambient frustration.

---

## What this gives you

- **Six agent roles out of the box** — and any number of custom roles you add. Each role has a persona stub (`SOUL.md`) and a professional-standards floor (`standards.md`); both are always-injected at skill-load time. (§7 of the spec)
- **A seven-step learning loop** — capture → tag → inject → apply → record → detect re-capture → escalate. Break any link and the owner is repeating themselves; the system catches that and demotes the responsible skill. (§1.1 + §3)
- **A 5-rung autonomy ladder** — L1 draft-only through L5 auto-irreversible. Promotion needs *three* inputs: track record, structural compliance, learning fidelity. None of these alone earns trust. (§4)
- **A read-only watcher** — `SystemSentinelAgent` watches everything, mutates nothing. Her only output is a kanban task to you. The alarm, not the firefighter. (§5)
- **A single voice to the world** — one mailbox per deployment by default, owned by the Chief of Staff. Specialists draft; CoS sends. Multi-channel ingress (email, chat, Signal, Slack) normalizes here. (§2.3)
- **Vendor-neutral by design** — no framework code names a model or provider. Your deployment picks; the framework treats them as opaque strings. Local, hosted, mixed, any OpenAI-compatible endpoint. (§1.3)
- **Markdown projection** — the database is canonical; your vault is the human-readable projection. No more "vault and DB drift." (Appendix A.4 of the spec)

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

agency status                # Hermes detected? profiles up? manifest valid?
agency next                  # actionable next-steps for your specific state
agency audit                 # framework self-audit + skill audits
agency panel                 # read-only control panel at localhost:9118
```

### Talk to your agency

```bash
agency chat                  # interactive REPL with your CoS
agency chat "draft a brief note declining the speaker invitation"   # one-shot
agency chat --profile loriah --verbose "summarize my goals.md"      # see which rules fired
```

`agency chat` loads the profile's SOUL.md + standards.md + all applicable
supervised-learning rules, then sends your message to the configured provider.
This is the fastest way to confirm the framework is alive and your corrections
are influencing responses.

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
