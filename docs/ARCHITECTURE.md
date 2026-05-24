# Architecture

HermesAgency is a multi-agent framework layered on top of the
[NousResearch Hermes engine](https://github.com/NousResearch/hermes-agent),
designed around one architectural commitment:

> Every correction the owner gives is captured, tagged, propagated to
> every relevant agent across the agency, and applied without the
> owner repeating themselves.

If the owner has to re-teach the same correction across contexts,
that's a system failure here, not an ambient frustration. The whole
architecture exists to keep that failure from happening — and when
it happens anyway, to detect it and demote the responsible skill.

---

## The seven-step learning loop (the spine)

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
   ┌───┼───┐
   ▼   ▼   ▼
 AUTONOMY VERIFIER KANBAN
  LADDER  SEAM    SEAM
   │
   ▼
 SENTINEL  (watches everything, mutates nothing)
```

The seven steps (see [`docs/LEARNING_LOOP.md`](LEARNING_LOOP.md) for
detail):

1. **Capture** — the correction lands in `learning_rules`.
2. **Tag** — across skill / role / voice axes.
3. **Inject** — every relevant skill pulls applicable rules into its
   prompt at skill-load.
4. **Apply** — the agent uses the rule in its next decision.
5. **Record** — `firings.record()` confirms the rule influenced
   behavior.
6. **Detect re-correction** — inline cosine similarity check
   against the last 90 days.
7. **Escalate** — demote the responsible skill, file a kanban alert,
   surface to the operator.

Break any link and the owner is back to re-teaching. Every other
subsystem composes around this chain.

---

## The five system seams

1. **Learning** (`_framework/learning/`) — the spine described above.
   The thing the rest of the framework exists to keep functioning.

2. **Autonomy** (`_framework/autonomy/`) — the L1-L5 ladder. Every
   skill earns its level. Promotion needs three inputs holding
   simultaneously: track record, structural audit compliance,
   learning-loop fidelity. See [`docs/AUTONOMY.md`](AUTONOMY.md).

3. **Verifier** (`_framework/verifier/`) — typed completion,
   fail-closed. Every kanban-completing skill declares
   `## Verifier criteria`; zero criteria refuses completion.

4. **Kanban** (`_state/kanban.db`) — cross-profile work channel.
   Per-profile processor crons claim tasks assigned to them. Two
   link types — `blocks` (gates) and `tracks` (aggregates) — to
   avoid umbrella-deadlock.

5. **Send-guard** (`_framework/send_guard/`) — outbound-mail
   validation. Access list → hard ceilings → hard-rule validators.
   Override attempts record firings so the loop sees the breaches.

---

## Vendor-neutral by design

No framework code names a model or provider. Any OpenAI-compatible
endpoint works — local Ollama, llama.cpp, MLX; hosted OpenAI,
Anthropic, DeepSeek, Mistral, Cohere, Google, OpenRouter, Groq,
Together; mixed. The framework reads `defaults.provider` from
`deployment.yaml` as an opaque string.

The audit's `framework-vendor-leak` rule enforces this. Run
`agency audit --self` — vendor leaks are ALWAYS_BLOCK findings.

Vendor identity belongs in the deployment. Choose freely.

---

## The owner-agency interface model (one face)

```
  OWNER
   │ (email, chat, Signal, Slack, dashboard, …)
   ▼
 ┌──────────┐
 │   COS    │  ← single conversational surface for the owner
 └──────────┘  ← single inbound/outbound surface for the world
   │     ▲
   │     │   (via kanban — see §17.10 of master plan
   ▼     │    for the cross-profile channel)
 ┌────────────────────────────────────────────┐
 │  KB · Sentinel · Analyst · BD · Writing   │  specialists
 └────────────────────────────────────────────┘
```

The default deployment ships single-mailbox: only ChiefOfStaff has
an outbound mailbox. Specialists draft; CoS sends. The world sees
one agency.

Deployments can override (give specialists their own mailboxes) —
the framework supports it. The default just ships single-mailbox
because that's what small-agency owners actually want.

---

## Curator-subject separation

Three nested layers of "the watcher is not the doer":

- **AnalystJudge judges ChiefOfStaff's work output.** Adversarial
  review of drafts, plans, decisions.
- **AnalystJudge curates the learning corpus that governs CoS.**
  Rules go in through Analyst's review, not CoS's self-judgment.
- **SystemSentinel watches everything, including AnalystJudge.**
  Sentinel cannot mutate state outside her own table — she can't
  influence what she's watching.

When AnalystJudge's own artifacts need review, the chain steps up
to SystemSentinel (structural compliance) and to the owner
(qualitative judgment).

---

## Adding new agents

Six default roles ship: ChiefOfStaff, KnowledgeBase,
SystemSentinel, AnalystJudge, BusinessDevelopment, WritingSupport.
But the framework supports N roles from day 1 — adding a
`FinanceAgent`, `LegalAgent`, `ItOpsAgent` is a deployment-level
config change, not a framework PR.

Mechanism: drop a directory under `_framework/roles/<id>/` (or the
deployment's `~/.agency/custom-roles/<id>/`) with a starter-skill
manifest, role description, and default cadence; list it in
`deployment.yaml::profiles`. The framework discovers it by
directory convention. See [`docs/ROLES.md`](ROLES.md).

---

## Layout summary

```
hermes-agency/                       (framework — github)
├── _framework/
│   ├── learning/       the spine (§3 of spec)
│   ├── autonomy/       L1-L5 ladder + graduation gate
│   ├── verifier/       typed completion + 10 criterion types
│   ├── sentinel/       events.db + cron monitors
│   ├── send_guard/     outbound mail validation
│   ├── audit/          7-category audit engine
│   ├── scaffolds/      scaffold-skill / -script / -profile
│   ├── ops/init/       agency init wizard (3 tiers)
│   ├── constants.py    brand-agnostic path constants
│   └── invariants.yaml single source of truth
├── templates/profiles/<role>/        per-role SOUL + standards
├── docs/                              public-facing documentation
├── DEVELOPMENT_PLAYBOOK.md            quality floor for all artifacts
├── hermes_agency/cli.py               the `agency` command
└── install.sh                          bootstrap script

~/.agency/                            (deployment — operator-owned)
├── deployment.yaml                    the manifest (owner picks)
├── framework-version.lock             pinned framework version
├── framework-vault/                   deployment-local copies of
│   ├── MASTER_PLAN.md                  shared docs Sentinel watches
│   └── DEVELOPMENT_PLAYBOOK.md
├── profiles/<id>/                     per-agent content
│   ├── SOUL.md                        always-injected identity
│   ├── standards.md                   always-injected quality floor
│   ├── skills/                        playbook-compliant skills
│   ├── scripts/                       cron scripts
│   └── ...
└── _state/                            shared cross-profile state
    ├── learning.db                    the spine's DB
    ├── autonomy.db                    L1-L5 history per skill
    ├── kanban.db                      work channel
    ├── events.db                      Sentinel's event log
    └── heartbeats.db                  per-component liveness
```

Detail for each subsystem:
[LEARNING_LOOP](LEARNING_LOOP.md) ·
[AUTONOMY](AUTONOMY.md) ·
[SENTINEL](SENTINEL.md) ·
[ROLES](ROLES.md) ·
[DEPLOYMENT](DEPLOYMENT.md) ·
[PATCHES_TO_HERMES](PATCHES_TO_HERMES.md)
