# HermesAgency

**A multi-agent framework for small-agency owners who refuse to re-teach their AI ten times.**

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

> Requires Python 3.11+. **You do NOT need to install Hermes first** — the
> wizard detects an existing install or installs Hermes for you as Step 0.

```bash
# 1. Clone + install HermesAgency
git clone https://github.com/ajcrabill/hermes-agency ~/HermesAgency
cd ~/HermesAgency
./install.sh

# 2. Initialize your deployment (interactive wizard — pick a tier)
#    First question: Hermes engine
#      [a] Already installed → detect + layer on top
#      [b] Install Hermes for me now (~2-5 min, downloads ~150 MB)
agency init                     # T1 (5-10 min): defaults across all 6 agents
agency init --tier 2            # T2 (15-30 min): OAuth + ingress configuration
agency init --tier 3            # T3 (45-60 min): deep interview, exemplar capture

# 3. Verify the spine
agency status                   # Hermes detected? profiles up? manifest valid?
agency next                     # what to do next based on actual state
agency capture "test correction"   # rule appears in _state/learning.db
agency audit                    # framework self-audit + skill audits

# 4. Open the control panel
open https://localhost:9118/control-panel
```

**If Hermes is missing on an existing deployment** (e.g. you installed
HermesAgency separately from Hermes, or moved to a new machine):

```bash
agency init --hermes-only       # just Branch A/B; doesn't touch your manifest
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
