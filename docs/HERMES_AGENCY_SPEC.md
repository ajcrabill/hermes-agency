# HermesAgency — Specification

**Version:** v0.19.1-spec (2026-05-24) — *also: v0.09 of the 9th version (see §0.5)*
**Status:** Living spec — tracks shipped releases
**Author:** AJ Crabill — AI Developer for Good Ancestor ([www.GoodAncestor.com](https://www.GoodAncestor.com))
**Home:** `github.com/ajcrabill/hermes-agency` (MIT)

---

## 0. Document purpose

This is the build + design specification for **HermesAgency** — a
continuously-learning, multi-agent plugin for [NousResearch's Hermes
Agent](https://github.com/NousResearch/hermes-agent), built for
small-business owners who don't want to re-teach their AI ten times.

The spec was written before code so the architecture could be reviewed,
revised, and locked before any building. AJ is the first customer; his
v7 system is migrating to HermesAgency via the v7-migration tool
(`agency migrate v7`).

This document is the source of truth for the framework's design.
Sections §0–§15 describe the architecture; §16 (change log) tracks
every formal revision since v0.1, including all release-level
versions. New features land through the release cycle and accrete
in the change log; sections above are revised when the underlying
architecture changes.

### Architectural arc (read this first if you're new)

HermesAgency is the 9th version of a personal AI chief-of-staff
project. The 9-version lineage (with hardware, model, and runtime
transitions per version) is in §0.5. The arc within v9 — the
current architectural foundation — is:

1. **v0.1–v0.14** (v8 of Loriah, parallel-framework era) —
   implementation grew as a "parallel framework that layered on
   Hermes" via text-anchor patches into Hermes' source. That
   approach proved fragile against Hermes refactors and meant
   HermesAgency had its own CLI, state directory, panel, runtime —
   competing with Hermes rather than extending it.
2. **v0.15** — narrative reset: §1.4 "Plugin discipline" added
   `agency hermes-patches systems` as the honesty surface for what
   was actually wired vs. parallel.
3. **v0.16** — install simplified to 4 steps; bootstrap stopped
   installing Hermes for the user; migration extended to take a
   v7-home directory.
4. **v0.17 — architectural pivot (start of v9 of Loriah).**
   Hermes' documented plugin API was discovered. All 7 reliability
   systems re-wired as Hermes lifecycle hooks (`pre_llm_call`,
   `pre_tool_call`, `post_tool_call`, `transform_tool_result`,
   `on_session_start`, `on_session_end`). Text-anchor patches
   retired. `/agency` slash command inside Hermes is the
   supervisory surface.
5. **v0.18** — verifier enforcement: `transform_tool_result` hook
   runs ad-hoc verifier criteria against tool outputs; failures
   become actionable LLM errors. Deprecated patches module deleted.
6. **v0.19–v0.22** — remaining structural cleanup to bring the
   codebase fully in line with "plugin-from-the-start" design:
   in-Hermes setup interview, flatten `_framework/<x>/` →
   `hermes_agency_plugin/<x>/`, move state from `~/.agency/` to
   `~/.hermes/agency-state/`, register profiles + skills with
   Hermes' native registries, demote standalone `agency` CLI to a
   thin shim, agentskills.io conformance, PyPI distribution. See
   §13.7 for the explicit closure plan.

### 0.5 Lineage — this is the 9th version

HermesAgency is the 9th major version of a personal AI chief-of-staff
project that's been running, breaking, and getting rewritten on and
off for years. Each rewrite kept the same ambition — *"a chief-of-
staff who actually learns my preferences and earns autonomy on them"*
— and replaced the foundation under it: different hardware, different
runtimes, different models, different architectural shapes. Each
rewrite was triggered by the previous version hitting a wall that
couldn't be patched without redoing the foundation.

The simplicity of the current architecture is hard-won. v0.17+ is
the first version that gets out of the way of itself — the seven
reliability systems are documented hooks into a stable runtime
contract — and that simplicity is only obvious in retrospect. Eight
prior versions made the case for it the long way around.

| # | Year | Foundation | Hardware | Model | What changed; what it taught |
|---|---|---|---|---|---|
| **1** | early | OpenClaw on a VPS | cloud VPS | Claude Sonnet | First long-running deployment. Cloud-hosted, single-agent, instruction-driven. Taught: instructions-only memory drifts. The chief-of-staff needs durable state, not just a long system prompt. |
| **2** | | Claude Cowork | esb-m1 (64 GB) | Claude Opus | Moved off the VPS onto a local workstation. Bigger context, much faster iteration, but still instruction-only. Taught: hardware/model upgrades don't fix architectural debt — the same drift returns at a higher cost. |
| **3** | | (complete rewrite, same stack) | esb-m1 | Claude Opus | First clean-slate redo. State written down to files the agent had to read explicitly. Taught: state-in-instructions ("remember to check X") is still drift; state has to be *loaded by code*, not by a remind-the-agent step. |
| **4** | | **[dCoS](https://github.com/ajcrabill/dCoS)** *(archived)* | esb-m1 | Anthropic | "Digital Chief of Staff" — first version with a proper SQLite-backed state model, vault as canonical store, goal-directed operation. Single-agent. Taught: the goal-directed-loop pattern (every action traces back to an obligation) is the right shape. Single agent is the wrong shape — a CoS isn't a researcher, a librarian, and a writer all at once. |
| **5** | | dCoS rebased onto **Hermes Agent** | esb-m1 | Anthropic | First version on a real agent runtime. Stopped reinventing the conversation loop, the tool-call layer, the skill system. Taught: the *runtime* should be NousResearch's problem, not mine. My value-add is the supervisory layer. |
| **6** | | major revamp; Hermes update + **DeepSeek** | esb-m1 | DeepSeek | Hermes shipped a major update that changed the skill-load path; same time, moved off Anthropic to DeepSeek for cost. Taught: vendor-lock at the framework level is a trap. Anything baked-in about Anthropic's API shape had to be ripped out and abstracted. The vendor-neutral architectural commitment (spec §1.3) crystallized here. |
| **7** | | major rewrite; Hermes profiles + kanban | esb-m1 | DeepSeek | Hermes shipped profiles (multi-identity per install) and a built-in kanban. The whole "one chief-of-staff" → "an agency of specialists" reframing happened here. Six (then seven, with Finance) agent roles. Cross-profile work via kanban tracks-links. Taught: the supervisory layer (learning loop / autonomy ladder / verifier / send-guard / sentinel / audit) IS the product; the agents themselves are differently-pointed instances of the same underlying machinery. This is the version AJ runs personally at `~/.hermes/context/loriah/` while v8 and v9 were under construction. |
| **8** | 2026 | **HermesAgency** as a standalone soft-fork of Hermes | esb-m4 (128 GB) | DeepSeek + local (Qwen 3.6, Gemma 4) | Moved to a bigger workstation; same time, took everything v7 had learned and re-implemented it as a separate framework that *layered on* Hermes via text-anchor patches into its source. Sixteen public releases (v0.1–v0.16 of the repo) refined the seven reliability systems. Taught: "framework over runtime" is the wrong shape when the runtime has its own plugin API. The text-anchor patches turned out to be the symptom of trying to be a parallel framework instead of an actual plugin. |
| **9** | 2026 | **HermesAgency** as a real **Hermes plugin** | esb-m4 | DeepSeek + local | The v0.17 architectural pivot. Discovered Hermes' documented plugin API (lifecycle hooks: `pre_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_tool_result`, `on_session_start/end`) and re-wired every reliability system as a Hermes hook instead of a source patch. All 7 systems Hermes-extending. `/agency` slash command inside Hermes. Hermes-update-resilient (plugin API is a stable contract). v0.18+ continues the cleanup — verifier enforcement (shipped), in-Hermes setup interview (v0.19), structural rename + state collapse (v0.20), agentskills.io conformance (v0.21), PyPI distribution (v0.22). This is what the spec said HermesAgency would be from §1.1 of v0.1 — finally true in implementation. |

**Pattern across the 9 versions.** Each transition was triggered by
one of three forces:

1. **Hardware ceiling.** v1 → v2 (VPS to local) and v7 → v8 (64 GB to
   128 GB) both came from "the work outgrew the box." Each move
   unlocked workflows the previous box couldn't run.
2. **Runtime contract change.** v6 (Hermes major update) and v7
   (Hermes profiles + kanban) are versions where NousResearch's
   own roadmap broke the seams the previous version was built on.
   These weren't AJ's choice — they were forced rewrites — but each
   time they returned a better foundation than the one being
   replaced.
3. **Architectural mistake taught.** v1 (instructions-only memory),
   v3 (state-in-instructions), v8 (parallel framework). Each of
   these failures was inherent in the shape of the design; no patch
   could fix them. They drove total redesigns toward state-in-code,
   then goal-directed-loop, then real-plugin-discipline.

The current shape — Hermes plugin with seven hooks — is the answer
that survives all three forces:

- Hardware ceilings: plugin is cheap to relocate; state moves with it.
- Runtime contracts: the plugin API IS the contract; Hermes' internal
  refactors don't break us.
- Architectural mistakes: every reliability system is a Hermes hook,
  not a parallel call path; there's no parallel-framework drift
  pressure.

Eight prior versions failed in instructive ways. v9 is the version
where each failure mode has a structural answer rather than a
patch.

### Dual-version notation

The spec carries two version numbers:

- **Public release version** (e.g. `v0.18.0`): semver against the
  `hermes-agency` repo on GitHub. This is what `pip install
  hermes-agency==0.18.0` resolves to, and what `agency --version`
  prints.
- **"v0.M of the 9th version"** (e.g. *v0.05 of the 9th version*):
  an internal counter that started fresh at v0.17 when the plugin-
  API pivot reset the architectural foundation. v0.17.0 = v0.01;
  v0.17.1 = v0.02; v0.17.2 = v0.03; v0.18.0 = v0.05; etc.

The 9th-version counter signals what v0.17+ is *relative to* v0.1–v0.16:
not a continuation, but a re-foundation on a different architectural
contract. v0.1–v0.16 were v8 of Loriah (parallel-framework era).
v0.17+ are v9 (proper-plugin era).

### Practical answer for new readers

"Is this production-ready?"

- **The runtime is.** Hermes itself (NousResearch's work) is
  production-grade and has been for many releases.
- **The supervisory layer is in early plugin release.** v0.17 landed
  the plugin pivot; v0.18 added verifier enforcement; v0.19–v0.22
  close the remaining structural gaps. The architectural shape is
  now the right shape; the code is steadily working its way into
  that shape. The seven reliability systems are functioning today,
  enforced via documented Hermes lifecycle hooks.

---

## 1. The promise — what this plugin is for

**HermesAgency is a multi-agent framework built as a plugin to
NousResearch's powerful Hermes agentic engine.** Designed *for* and
*by* small-business owners, HermesAgency pulls together the suite of
capabilities every small business wants and needs but typically can't
afford. It's where the powerful, always-working aspects of
*technological intelligences* (the agents) collaborate with the
ingenuity and creativity of *biological intelligences* (the humans).
Together, with a **7-part continuous learning framework** designed
from the ground up to rapidly expand the agents' understanding of
the human's goals and values, HermesAgency gives business leaders
access to the advantages of companies many times their size and
revenue — without sacrificing the privacy and ownership of their
data and intellectual property, and without getting locked into
big-tech ecosystems.

**The one-line operational promise:** every correction the owner
gives is captured, tagged, propagated to every relevant agent across
the agency, and applied without the owner repeating themselves. The
autonomy ladder lets agents earn more independence over time — but
only when the learning loop is provably working. The system tells
the owner when it isn't.

The collaboration model is explicit: technological intelligences
contribute *consistency, persistence, parallel attention, and
tireless follow-through*; biological intelligences contribute
*judgment, taste, originality, ethical anchoring, and the moments
of insight that re-direct the work*. Neither alone is enough for a
small business to compete against operations many times its size.
Together — with the right learning loop binding them — they can.

### 1.1 The seven-step learning loop

For HermesAgency to deliver on its promise, an unbroken chain must hold
for every owner correction:

1. **Capture** — the correction lands in the learning corpus
   (`_state/learning.db.learning_rules`).
2. **Tag correctly** — across the right skills + cross-cutting tags
   (`general`, role-keys, voice-attributes).
3. **Inject at skill-load** — every relevant skill pulls applicable
   rules into its prompt before deciding anything.
4. **Apply** — the agent uses the rule in its next decision.
5. **Record** — `firings.record()` confirms the rule influenced behavior.
6. **Detect re-correction** — semantic similarity check on the next
   capture against the last 90 days. Similar correction = the loop
   broke somewhere upstream.
7. **Escalate on re-correction** — demote the responsible skill's
   autonomy + file a visible alert + record the loop-break event for
   diagnosis.

Break any link and the owner is back to re-teaching. Every architectural
choice in §2-§12 serves the integrity of this chain.

### 1.2 Why this is the differentiator

Most "AI assistant" tools forget context between sessions, remember
within a session but not across them, or remember statically but can't
be corrected without manual prompt-engineering. The combination —
**explicit correction → cross-skill propagation → autonomy gated on
learning fidelity** — is what makes the framework actually save time.

If a small-agency owner has to repeat the same correction across
contexts, the system has *cost* them attention rather than saved it.
HermesAgency makes "the owner is repeating themselves" a visible system
failure mode, not an ambient frustration.

### 1.3 Vendor-neutral by design

**HermesAgency makes no assumption about which model or provider sits
behind it.** The framework speaks OpenAI-compatible API. Beyond that,
the deployment chooses: local-only (Ollama, llama.cpp, MLX), hosted-
only (any compatible vendor), mixed local-and-hosted with fallback,
single-vendor, multi-vendor — all are first-class deployment options.

This is an architectural commitment, not a configuration convenience:

- **No framework code names a vendor.** The audit doesn't check for
  any specific provider; the scaffolds don't generate vendor-flavored
  output; the autonomy ladder doesn't treat any model as "smarter";
  Sentinel doesn't favor any backend. If you grep the framework for a
  vendor name, you should find none.
- **Vendor identity lives in `deployment.yaml`.** A deployment names
  whatever provider(s) it uses there. The framework reads them as
  opaque strings.
- **The audit enforces this.** `audit-alignment.py` has a rule
  (`framework-vendor-leak`) that flags any framework-level file
  containing a vendor name (OpenAI / Anthropic / Mistral / DeepSeek
  / Cohere / Google / etc.). Vendor names are allowed in templates,
  deployment-specific files, and documentation that explicitly
  enumerates "compatible vendors" — but not in core framework code.
- **Why this matters:** small-agency owners may have strong
  preferences (cost, sovereignty, privacy, local-only,
  political/ethical, vendor relationships). The framework should be
  invisible to those preferences. Adding a new compatible provider
  is a deployment.yaml entry, not a framework PR.
- **Documentation enumerations are allowed.** Lists like "any
  OpenAI-compatible endpoint — including local Ollama, llama.cpp,
  Anthropic, OpenAI, DeepSeek, Mistral, Cohere, OpenRouter, Groq,
  and others" appear in docs as examples of what BYO means. The
  point is: this is an open list, the framework treats them all the
  same.

When this spec or the playbook mentions a vendor anywhere outside an
explicit "compatible-with" enumeration, that's a bug. Lynda's audit
catches it.

### 1.4 Plugin discipline — Hermes is the runtime, always

**HermesAgency is a plugin, not a parallel framework.** Every
reliability system it adds (the 7 in §1.7) must be expressed as a
Hermes hook — a patch into Hermes' execution path, or a shim that
reads/writes Hermes' own state. The agency CLI exists for setup,
audit, capture, and supervision. It does not exist as an alternate
runtime.

Equivalently: there is no daily-use command in HermesAgency that
replaces `hermes chat` or `hermes run <skill>`. If you find yourself
typing `agency chat`, the integration is broken — fix the patch,
don't normalize the workaround.

This is a constitutional rule, not a style preference. Through
v0.1–v0.14 the implementation drifted: each new subsystem (CRM,
finance, coaching, prototyping, goals, quality, cost, OTP, panel,
runtime/chat) got built as `_framework/<x>/` with its own state DB
and its own code paths. The agency framework called these modules
itself; Hermes never touched them. The result was a framework that
ran alongside Hermes instead of one that extended it — and the
operator-facing question "how do I use it?" had no clean answer
because the answer the spec implied (`hermes chat`) wasn't
actually enriched.

**v0.17.0 closed the structural integration gap** by pivoting from
text-anchor patches into Hermes' source (the v0.2–v0.16 approach,
fragile against Hermes refactors) to Hermes' **documented plugin API**.
HermesAgency's plugin lives at `hermes_agency_plugin/__init__.py`,
gets symlinked into `~/.hermes/plugins/hermes-agency/` by the bootstrap,
and is discovered by Hermes' `PluginManager` on next launch.

The plugin's `register(ctx)` function wires our reliability systems
into Hermes' lifecycle hooks (`pre_llm_call`, `pre_tool_call`,
`post_tool_call`, `on_session_start`, `on_session_end`) and adds
`/agency <subcommand>` as an in-session slash command.

`agency hermes-patches systems` remains as the honesty surface —
running it on a v0.17 install shows 7/7 systems wired. Any change
that adds new `_framework/<x>/` state-owning subsystems without a
corresponding plugin hook is an architectural deviation tracked
for the next release. The audit (§14, planned rule
`framework-parallel-state-leak`) will eventually enforce this at
commit-time.

The discipline:

- **New reliability systems** must propose their Hermes-hook
  shape (patch into a Hermes file, or shim over a Hermes table)
  before any standalone code is written.
- **Existing parallel modules** (autonomy, verifier, send-guard,
  any of the v0.3+ subsystems that ended up parallel) are
  architectural debt to be repaid via the v0.16–v0.19 plan.
- **`agency hermes-patches systems`** is the public source of
  truth for whether the discipline is being kept.

### 1.5 The three pillars — and why this matters now

HermesAgency stands on three pillars:

1. **Powerful Autonomous Team.** Six role-specialized agents (or seven,
   with FinanceAgent) — Chief of Staff, Knowledge Base, System
   Sentinel, Analyst Judge, Business Development, Writing Support,
   Finance — that route work through each other via Hermes' kanban,
   with CoS as the single face to the world. Specialists draft, CoS
   sends. Each agent carries its own SOUL.md, standards.md, and a
   curated skill catalog. Not a gimmick — a small-business-shaped
   organizational chart in software. (§2, §7)

2. **Continuous Context Learning.** Every correction the operator
   gives is captured to a learning corpus, tagged across skills and
   roles, injected into every relevant prompt at load time, and
   applied without the operator repeating themselves. The recapture
   detector catches when a correction stops landing — the loop
   breaking is itself a system signal, not silent drift. Autonomy
   gates earn upward only when the learning loop is provably
   working. (§1.1, §3, §4)

3. **Complete Privacy & Data Control.** Every byte of state — the
   learning corpus, the agency vault, conversation history, kanban,
   sentinel events, audit findings — lives on your hardware under
   `~/.hermes/agency-state/`. No cloud dependency for the agency
   layer. Inference provider is your choice (local Ollama / Qwen /
   Gemma / DeepSeek / OpenAI / Anthropic / any OpenAI-compatible
   endpoint); the framework names no vendor and treats providers
   as opaque strings (§1.3). You can swap providers, mix local
   with hosted, or air-gap to local-only inference entirely at any
   time. Your IP, your ideas, your corrections, your operational
   memory: yours.

### 1.6 Why this matters now — the big-tech contrast

Every large platform is rolling out the same feature set: AI
assistants, multi-agent workflows, persistent memory, learning
from corrections, integrated calendaring and email. The capability
that distinguishes small-business work from large-enterprise work
is collapsing — fast. **A small-business owner without these tools
is at a real disadvantage against competitors who have them.**

But the big-platform versions of these features come at a price
the spec is explicit about refusing:

- **Ecosystem lock-in.** Once your obligations, contacts, IP, and
  drafting workflows live inside a platform, switching means
  abandoning the institutional memory you've built. The cost rises
  monotonically with usage.
- **Data exfiltration as the price of admission.** Your IP, your
  client information, your private deliberations, your unfinished
  ideas, your strategic thinking — all of it gets uploaded as the
  cost of using the assistant. "We don't train on your data" is
  the current promise; it's not architecturally enforced and the
  terms can change.
- **Per-seat economic model.** The features scale with your team
  size, not with the value they unlock. Small businesses pay
  proportionally more than large ones for the same capability.

HermesAgency's position: **a small-business owner should be able to
have all the same capabilities — continuous learning, multi-agent
workflows, integrated communication, autonomy-graded delegation —
without surrendering the data, IP, or ideas that make their business
distinct.** Not by refusing the capability (that's losing the
competitive race) but by owning the implementation.

The architectural commitments that make this true:

- **MIT-licensed, open source** — full code visibility; nothing
  hidden, nothing under a SaaS pricing curve. (Spec entire.)
- **Runs on your hardware** — Hermes Agent + HermesAgency operate
  on your machine; the agency layer has no cloud dependency. Your
  state never leaves your filesystem unless you explicitly
  configure it to.
- **Vendor-neutral inference** — pick your model, mix providers,
  go local-only with Ollama / Qwen / Gemma if you want zero data
  egress. §1.3 enforces this in code (`framework-vendor-leak`
  audit rule).
- **No telemetry, no phone-home** — the framework does not call
  out to any AJC- or Good-Ancestor-controlled endpoint. Updates
  are explicit `git pull` operations.
- **Your IP stays yours** — corrections, learning rules, vault
  documents, drafts, prior decisions all live in your filesystem
  under paths *you* control. The framework reads from them but
  never copies them anywhere.

The competitive thesis is straightforward: **the small business
that masters their own AI agency wins.** HermesAgency is the path
that doesn't require trading ownership of their IP for the
capability.

### 1.7 The seven reliability systems

The exhaustive list of what HermesAgency adds to Hermes:

| # | System | Hook into Hermes |
|---|---|---|
| 1 | Supervised learning loop | Plugin's `pre_llm_call` hook injects applicable rules into the user message each turn |
| 2 | Autonomy ladder (L1–L5) | Plugin's `pre_tool_call` hook consults `_framework.autonomy` and blocks tool calls the skill lacks authority for |
| 3 | Verifier (per-skill criteria) | Plugin's `post_tool_call` hook records completions; v0.18 adds `transform_tool_result` to enforce verifier criteria |
| 4 | System Sentinel (read-only) | Plugin's `on_session_start` / `on_session_end` hooks record session events; Sentinel reads from there + Hermes' own state |
| 5 | Kanban tracks-link type | Shim writes `tracks` rows into Hermes' own `kanban.db` |
| 6 | Send-guard (outbound mail gate) | Plugin's `pre_tool_call` hook filters for outbound-mail tools and runs `_framework.send_guard.evaluate` |
| 7 | Audit (weekly alignment) | Scheduled script reading Hermes state + agency state; produces findings, not actions |

**As of v0.17.0, all 7 systems are Hermes-extending** via the documented
Hermes plugin API. Earlier versions (v0.2–v0.16) used text-anchor patches
into Hermes' source — that approach proved fragile against Hermes refactors
and was retired when Hermes' plugin API was discovered (see §16 v0.17.0
change log entry). The remaining work (v0.18+) is policy depth, not
integration shape: verifier enforcement, send-guard hard-rule expansion,
and the migration-or-clean-install setup interview that runs as a Hermes
slash command (`/agency setup`).

---

## 2. Architecture overview

### 2.0 Plugin shape — the foundation everything else rests on

HermesAgency is a **Hermes plugin**, discovered via Hermes'
`PluginManager` at the standard plugin path:

```
~/.hermes/plugins/hermes-agency/   →  symlinked to the installed
                                       hermes_agency_plugin/ package
                                       (or pip-installed via entry point
                                       once on PyPI)
```

The package's `__init__.py` exposes a single function — `register(ctx)` —
which wires every reliability system into Hermes' documented lifecycle
hooks:

```python
def register(ctx) -> None:
    ctx.register_hook("pre_llm_call",     on_pre_llm_call)      # learning rule injection
    ctx.register_hook("pre_tool_call",    on_pre_tool_call)     # autonomy gate + send-guard
    ctx.register_hook("post_tool_call",   on_post_tool_call)    # verifier observation
    ctx.register_hook("on_session_start", on_session_start)     # Sentinel open
    ctx.register_hook("on_session_end",   on_session_end)       # Sentinel close
    ctx.register_command("agency", handler=handle_agency_command, description=...)
```

**Direct consequences of being a plugin (not a parallel framework):**

1. **Hermes is the runtime.** Always. `hermes` is THE binary. `/agency
   <subcommand>` is THE supervisory interface inside Hermes. There is
   no `agency chat`, no parallel runtime, no parallel CLI surface for
   daily use. A standalone shell-side `agency` command exists only as
   a thin shim for non-interactive contexts (cron jobs, CI scripts).
2. **State lives next to Hermes' state.** `~/.hermes/agency-state/*.db`
   — alongside Hermes' own `state.db` / `kanban.db` / `scheduler.db`.
   No separate `~/.agency/` world. (Currently in transition; the
   v0.20 release completes the move.)
3. **Profiles are Hermes agents.** The six+ agent roles (CoS, KB,
   Sentinel, AnalystJudge, BD, Writing, Finance) are registered into
   Hermes' agent registry via `ctx.register_agent(...)` on plugin
   load. Hermes already knows how to load + chat with multiple agent
   identities; we contribute identities rather than building our own.
   (Currently in transition; v0.20 completes the registration move.)
4. **Skills are agentskills.io-compatible.** Each `.md` skill file
   the plugin ships is registered via `ctx.register_skill(...)` on
   plugin load. Hermes runs them; we just contribute the catalog.
   (v0.21 brings the skill files into conformance with the
   agentskills.io open standard the Hermes README points at.)
5. **No `agency init` wizard.** First-run setup is a Hermes skill
   (`/agency setup`) that CoS runs when she sees the deployment is
   not yet configured. The bash wizard is a v0.1–v0.17 vestige
   removed in v0.19.

These are the design principles. The rest of §2 describes what gets
built on top of them.

### 2.1 The six agents

HermesAgency v0.1 ships with six agent roles. A deployment activates any
subset (minimum three: CoS + KnowledgeBase + SystemSentinel; the others
graduate from skill-clusters as workload justifies). Each role has a
template profile, persona stub, and starter skills.

| Role | Identity | Mode | Sends mail (default)? |
|---|---|---|---|
| **ChiefOfStaffAgent** | The owner's interface, top-level coordinator | Coordinate, communicate, real-time ops | **Yes — the only outbound mail surface** |
| **KnowledgeBaseAgent** | Classify, organize, retrieve | Knowledge work | No — work routed in/out via CoS + kanban |
| **SystemSentinelAgent** | Pure observability + audit; no action authority | Watch | No — read-only by design |
| **AnalystJudgeAgent** | Adversarial review, dossier, research, curation | Investigate, critique, judge | No — internal only |
| **BusinessDevelopmentAgent** | Lead-gen, opportunistic outreach (news-driven), journalist + podcast relationship building, CRM | Outbound intelligence | No — drafts handed to CoS for review + send |
| **WritingSupportAgent** | Author coaching (multi-author), staff workbook drafting, weekly newsletter | Content production | No — author correspondence flows through CoS |

**Default architecture: one mailbox per deployment, owned by CoS.**
External parties (collaborators, authors, journalists, leads) see one
face — the ChiefOfStaff. Specialist agents do the work; CoS is the
voice. Per §2.4 below.

Deployments CAN override the default (give a specialist agent her own
mailbox) — but only if there's a real reason the single-mailbox model
fails for that deployment. The framework's default ships single-mailbox
because that's what small-agency owners actually want: one persona to
manage, one outbound voice to maintain, one canonical send path to
audit.

### 2.2 The spine — learning loop integrity

The learning loop (§1.1) is the architectural spine. Everything else
composes around it:

```
                    OWNER CORRECTION
                          │
                          ▼
            ┌─────────────────────────────┐
            │     LEARNING SUBSYSTEM      │  (§3)
            │  capture → tag → inject →   │
            │       record → recapture     │
            └─────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ AUTONOMY │ │ VERIFIER │ │  KANBAN  │
        │  LADDER  │ │   SEAM   │ │   SEAM   │
        │   (§4)   │ │   (§6)   │ │   (§6)   │
        └──────────┘ └──────────┘ └──────────┘
              │
              ▼
        ┌──────────┐
        │ SENTINEL │  watches everything (§5)
        │   (§5)   │  fires recapture detector
        └──────────┘
```

Every agent loads applicable learning rules at skill-load time
(§3.3). Every consequential action passes through the autonomy gate
(§4.2). Every completion runs through the verifier (§6.1). Sentinel
watches the loop's health and fires alerts when it breaks (§5.3).

### 2.3 Owner-agency interface model — one face

The agency is **one face to the owner, and one face to the world**.
Both faces are ChiefOfStaff.

```
        OWNER
         │ (email, chat, Signal, Slack, dashboard chat tab, …)
         ▼
   ┌──────────┐
   │   COS    │  ← The owner's single conversational surface
   └──────────┘  ← The world's single inbound/outbound surface
    │     ▲
    │ via kanban (cross-profile channel — see §6.3)
    ▼     │
   ┌──────────────────────────────────────────┐
   │  KB · Sentinel · Analyst · BD · Writing  │  (specialists)
   └──────────────────────────────────────────┘
                 ▲
                 │ specialists draft / research / classify
                 │ CoS reviews + sends as the agency's voice
```

The owner's preferred channels (email, chat, Signal, Slack, whatever)
are **input methods to CoS**, not separate agent interfaces. The owner
does not message KnowledgeBase to ask for a research item, or Writing
to ask about author coaching — they message CoS, who delegates via
kanban to the right specialist, retrieves the result, and responds in
the agency's one voice.

This commitment shapes several downstream design choices:

- **One mailbox per deployment** (the CoS's). Other agents' email
  fields default to `null` in deployment.yaml.
- **One outbound voice / persona** that the audit can lint for
  consistency. Multiple personas multiplies the maintenance surface
  for no real win in the small-agency case.
- **Specialist agents draft, CoS sends.** The drafting agent owns the
  domain knowledge (BD owns prospect context; Writing owns book-coaching
  voice per author); CoS owns the voice + the send authority + the
  send-guard discipline.
- **All ingress channels normalize to "items for CoS to triage."** A
  Signal message and an email and a chat-tab DM all land in CoS's
  inbox-like surface and get triaged with the same logic.
- **The send-guard is simpler** — one outbound mailbox to watch, one
  set of recipients to whitelist, one authority to audit. (§6.4)

A deployment CAN open more mailboxes if it genuinely needs them — the
framework supports it; the default just doesn't ship that way.

### 2.4 Adding new agents — the framework expands with the agency

A deployment is not locked to the six roles in §2.1. Owners can add
new agents (e.g. a `FinanceAgent`, a `LegalAgent`, an `ItOpsAgent`)
without framework changes. The framework supports N agents from Day 1:

- **Profile discovery is on-disk.** `_framework/manifest.py` reads
  `deployment.yaml::profiles` — any role declared there is loaded.
  No hardcoded six-role enumeration anywhere in code. (Per the v7
  §17.0 dynamic-discovery work.)
- **Role registration.** New roles add an entry under
  `_framework/roles/` (or in the deployment's
  `~/.agency/custom-roles/` for deployment-private roles) declaring:
  default action classes, default starter skill manifest, default
  cadence profile, default reviewer (per §2.3 curator-subject).
- **No role-specific code paths.** Every framework subsystem treats
  agents uniformly — kanban-processor pattern, autonomy gate, audit
  rules, Sentinel observability. The only role-aware code is the
  scaffold templates (one per role) which are pure data.
- **Owner-agency interface model still holds.** Adding a FinanceAgent
  does NOT add a finance@ mailbox by default. Finance work flows
  through CoS like all other specialist work: owner asks CoS about
  Q3 burn → CoS delegates to FinanceAgent via kanban
  (`tenant=finance` or similar) → FinanceAgent produces a report →
  CoS surfaces the result in her voice.
- **Audit role taxonomy is extensible.** `_framework/invariants.yaml`
  defines role keywords for `skill-role-mismatch` detection
  (§9.7 of playbook). Adding a role adds keywords; existing skills
  in the wrong place get flagged automatically.

**Owner-action to add a new role to their deployment:**

```bash
agency add-role finance --persona identities/finance.md \
    --starter-skills cash-flow-tracker,burn-rate-monitor,vendor-research
# → creates ~/.agency/profiles/finance/, scaffolds starter skills,
#   registers the finance-kanban-processor cron, adds finance entry
#   to deployment.yaml, bootstraps L1 autonomy entries
```

**Framework-level addition (contributing a new role to the public
framework so all deployments can use it):**

A PR to `hermes-agency` that adds `_framework/roles/finance/` with
its starter-skill manifest, role description, default cadence, and
review posture. Once merged, every deployment can opt in via
`deployment.yaml`. Framework version bumps signal that new roles are
available.

The framework's six-role default is **a curated starter set**, not
the closed system. Expansion is by design.

### 2.5 Identity + Standards — two docs per agent, consistent names

Every agent profile carries **two always-injected identity documents**.
Same filenames across every agent — no per-role naming convention to
remember:

| Document | What it answers | What it shapes |
|---|---|---|
| **`SOUL.md`** | *Who am I in the world?* | Identity, persona, voice, tone, posture, relationships |
| **`standards.md`** | *What do I bring to the world? What quality floor will I refuse to fall below?* | Professional craft, non-negotiables, what good work looks like, what bad work looks like, self-evaluation against the standard |

Both files live at the profile root (`profiles/<id>/SOUL.md` and
`profiles/<id>/standards.md`). Both are always-loaded into the agent's
system prompt at skill-load time. **By convention, deployment.yaml
doesn't need to reference them** — they're loaded automatically if
present.

**The starter content varies by role; the filename never does.**
Each role's default `standards.md` covers what that role considers
its non-negotiable professional commitments:

| Role | What `standards.md` covers (default content) |
|---|---|
| **ChiefOfStaffAgent** | The owner's time + attention are the resources being stewarded. Single voice for the agency. Discretion. Follow-through. Never the bottleneck. |
| **KnowledgeBaseAgent** | Verifiable claims only. IP-alignment first, opinions last. Citation discipline. The agency's stated frameworks applied correctly. (KB's role-specific `accuracy.md` content, just under the consistent filename.) |
| **SystemSentinelAgent** | Her `standards.md` is short — it states her commitments (observe without acting, signal not noise, alerts are earned) AND **directly references the master plan + development playbook** as the canonical standards she watches over and holds herself + the rest of the fleet to. The reference is in the doc; the loaded artifact is still just `standards.md`. |
| **AnalystJudgeAgent** | Every approval carries reasoning. Every rejection names specific failure modes. Adversarial review without performative cynicism. Evidence threshold for `block` vs `revise`. |
| **BusinessDevelopmentAgent** | BD as craft, not numbers. Research before reaching out. Personalization is the floor. Never spray-and-pray. Value-first contact, always. |
| **WritingSupportAgent** | Serve the author's voice; never substitute yours. Coaching is questions before answers. Author-voice ≠ agency-voice. |
| **(custom roles, e.g. FinanceAgent)** | Same filename. Content describes that role's professional commitments. Reference shared docs if relevant (a FinanceAgent might reference accounting standards or a budget-policy doc). |

**The principle:** *standards.md is the agent's professional standards
source of truth. The content of that one file is whatever actually
captures the role's commitments — including references to other
documents the agent reads as part of her standards (master plan,
playbook, agency-voice-guide, etc.). The loaded artifact is always
just `standards.md`.*

**Framework ships defaults; deployments customize freely.** Each
template profile ships with its `SOUL.md.template` +
`standards.md.template`. Deployments edit, extend, replace, or delete
freely — these should reflect the owner's actual standards for the
role.

**Different from audit reference.** Sentinel and Analyst both *use*
the playbook as an audit reference — a document they check OTHER
artifacts against. That's loaded contextually by the audit/red-team
skills, not always-injected. `standards.md` is different: it
governs the agent's OWN work, always present in context.

**Why two docs instead of one merged file:**

- **Different revision cadences.** Persona evolves rarely; standards
  evolve as the agency learns + as the bar moves.
- **Different maintainer audiences.** Voice + relationship tuning vs.
  craft + quality tuning. Two files keeps each shorter and clearer.
- **Different audit checks.** Audit checks `SOUL.md` for tone
  consistency (no role-overlap); checks `standards.md` for testable
  commitments (e.g. "I always cite sources" should be verifiable in
  the agent's output).

**Audit rules:**
- `profile-missing-soul` — critical (no identity = no agent)
- `profile-missing-standards` — warn (owner may have intentionally
  removed; agent operates on persona alone, which is risky but allowed)

### 2.6 Curator-subject separation, formalized

Three nested layers of "the watcher is not the doer":

- **AnalystJudge judges ChiefOfStaff's work output** — adversarial
  review of drafts, plans, decisions. (§17.3 of v7 master plan.)
- **AnalystJudge curates the learning corpus that governs CoS** —
  rules go in through Analyst's review, not CoS's self-judgment.
- **SystemSentinel watches the whole system, including AnalystJudge** —
  the auditor of the auditor. Sentinel cannot mutate state, so she
  can't influence what she's watching.

When AnalystJudge's own artifacts need review, the chain steps up to
SystemSentinel for structural compliance + the owner directly for
qualitative judgment.

---

## 3. Learning subsystem — the spine

Framework-level subsystem at `_framework/learning/`. Every other subsystem
depends on it. Cannot be turned off in a deployment.

### 3.1 Schema

```sql
-- _state/learning.db

CREATE TABLE learning_rules (
    id              TEXT PRIMARY KEY,        -- short hash
    correction      TEXT NOT NULL,            -- the lesson, in owner's voice
    source          TEXT NOT NULL,            -- where it was captured (email/kanban/etc.)
    skill_tags      TEXT NOT NULL,            -- JSON array of skill tags + 'general' if cross-cutting
    role_tags       TEXT,                     -- JSON array: chief-of-staff, analyst-judge, etc. (cross-agent rules)
    voice_tags      TEXT,                     -- voice/persona attributes (e.g. 'firm', 'warm-not-flattering')
    is_hard         INTEGER NOT NULL DEFAULT 0,  -- 1 = deterministically checkable, 0 = soft
    status          TEXT NOT NULL DEFAULT 'active',  -- active | suspended | superseded
    replaced_by     TEXT,                     -- if superseded
    embedding       BLOB,                     -- vector for similarity search (deployment picks the embedding model)
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    notes           TEXT
);

CREATE INDEX idx_lr_status ON learning_rules(status);
CREATE INDEX idx_lr_skill ON learning_rules(skill_tags);

CREATE TABLE firings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id         TEXT NOT NULL REFERENCES learning_rules(id),
    skill_tag       TEXT NOT NULL,            -- which skill was loading when this fired
    profile         TEXT NOT NULL,            -- which agent
    was_overridden  INTEGER NOT NULL DEFAULT 0,  -- if hard rule, did the agent try to violate?
    action_summary  TEXT,                     -- what action did the rule influence
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_fr_rule ON firings(rule_id, created_at);
CREATE INDEX idx_fr_skill ON firings(skill_tag, created_at);

CREATE TABLE recapture_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    new_rule_id     TEXT NOT NULL,
    similar_to      TEXT NOT NULL,            -- prior rule id
    similarity      REAL NOT NULL,            -- cosine 0.0-1.0
    skill_tags      TEXT NOT NULL,            -- skills implicated
    detected_at     TEXT NOT NULL,
    notified        INTEGER NOT NULL DEFAULT 0  -- owner alerted yet
);
```

### 3.2 Capture API

```python
# _framework/learning/correction_capture.py

def capture_correction(
    correction: str,
    source: str,
    skill_tags: list[str],          # required; at least one
    role_tags: list[str] | None = None,
    voice_tags: list[str] | None = None,
    is_hard: bool = False,
) -> str:                            # returns rule_id
    """Persist a correction. Side effects: embed for similarity,
    run recapture detection, optionally alert."""
```

Convenience wrappers per common capture path:
- `capture_from_kanban_comment(task_id, comment_text)` — owner replied to a kanban task with a correction
- `capture_from_inbox(message_id, classification)` — owner email containing a directive
- `capture_from_chat(session_id, turn_index)` — interactive correction during a Hermes chat

Every capture path runs through the same `capture_correction` core so
recapture detection (§3.5) sees everything.

### 3.3 Injection at skill-load

```python
# _framework/learning/rule_injection.py

def inject_for_skill(
    skill_name: str,
    profile: str,
    cap: int = 20,                  # per-skill injection cap
) -> str:                            # markdown text to append to skill prompt
    """Resolve applicable rules and return injection text.

    Resolution algorithm:
      1. Pull rules where skill_tags includes this skill_name
      2. UNION rules where 'general' in skill_tags
      3. UNION rules where role_tags includes this profile's role
      4. UNION rules where voice_tags overlap this skill's declared voice
      5. Order by (is_hard DESC, last_fired_at DESC NULLS LAST, created_at DESC)
      6. Cap at `cap` rules
    """
```

Wired into Hermes' skill-load machinery via patches to
`agent/skill_commands.py::_build_skill_message` and
`tools/skills_tool.py::skill_view`. Patches reapplied after Hermes
updates per the post-update re-apply hook pattern (§Appendix in
deployment docs).

### 3.4 Firings recording

Every rule that gets injected AND used calls `firings.record()`:

```python
firings.record(rule_id, skill_tag, profile, was_overridden, action_summary)
```

The model is prompted to record firings as part of its action loop —
skills include a "Step N: Record firings" instruction. The framework's
audit (§10) checks every skill has this wire.

Hard rules ALSO record via the send-guard / verifier when they catch a
violation attempt (`was_overridden=1`).

### 3.5 Recapture detection — the canary

```python
# _framework/learning/recapture_detector.py

SIMILARITY_THRESHOLD = 0.85          # tunable cosine threshold; embedding model chosen by deployment
LOOKBACK_DAYS = 90

def check_recapture(new_rule_id: str) -> RecaptureResult | None:
    """Called every time a rule is captured. Compares against last
    90 days of rules using embedding cosine similarity. If max
    similarity > threshold, returns a RecaptureResult with the
    matched prior rule + similarity score."""
```

When `check_recapture` returns a match:
1. Row appended to `recapture_events`
2. Event row appended to `events.db` (§5.2)
3. SystemSentinel files a kanban task: "Owner corrected the same
   thing twice — learning loop broken at skill X, rules Y/Z.
   Investigate the injection chain."
4. The responsible skill demotes one level (`autonomy.failure` event
   with reason `recapture: similarity=0.91`).

False-positive handling: owner can mark a recapture as "not a
recapture" via kanban comment `not-recapture` on the alert task. The
detector records the negative example and excludes from future
auto-alerts on the same prior rule. (No ML retraining; just a denylist.)

### 3.6 Tag conventions

- `skill_tags`: kebab-case skill names. At least one required.
  Special value `general` means "applies across all skills."
- `role_tags`: kebab-case role names from §2.1 set. Used for
  cross-agent rules (e.g. voice/style rules that apply to anyone
  speaking for the owner).
- `voice_tags`: free-form attributes like `firm`, `warm-not-flattering`,
  `we-not-i`. Skills declare which voice tags apply via frontmatter.

A rule tagged `[skill-foo, general]` injects everywhere. A rule tagged
`[role:chief-of-staff]` injects in every CoS skill. A rule tagged
`[voice:we-not-i]` injects wherever drafting happens.

### 3.7 Compliance report (cron, weekly)

`compliance_report.py` produces a Sunday morning summary:
- Rules captured this week (count + sample)
- Rules fired most (top 8 + override rate)
- Re-capture events (each is a system-failure flag)
- Rules never fired in 90 days (likely dead or mis-tagged)
- Top 5 skills by firings count (where learning loop is most active)
- Top 5 skills by 0-firings + >3 captured rules (where loop may be broken)

Delivered as a kanban task to the owner (`tenant=compliance`). Sentinel
authors it.

---

## 4. Autonomy ladder

Framework-level subsystem at `_framework/autonomy/`. Borrowed from v7
§16b with one structural addition.

### 4.1 The ladder

```
L1 draft-only         — drafts everything, sends nothing
L2 send-batched       — sends in supervised batches (owner reviews queue)
L3 send-single        — sends single items, notified to owner
L4 structural-change  — modifies DB rows, archives tasks, structural ops
L5 auto-irreversible  — auto-send to new contacts, delete data
```

Every skill starts at L1 — earned promotion only.

### 4.2 The action gate

Before any consequential action:
```bash
_framework/autonomy/autonomy_gate.sh <skill> <action-class> <profile>
```
Returns 0 if allowed, 1 if denied (skill not at required level).
Denials log + file a kanban task. (Same as v7.)

### 4.3 Promotion — three inputs (NEW in HermesAgency)

A skill is promoted L→L+1 only if **all three** hold:

1. **Track record** — N consecutive `clean_run` events above confidence threshold (default N=5).
2. **Structural compliance** — `audit-alignment.py --skill X --strict` returns 0 (no ALWAYS_BLOCK findings).
3. **Learning fidelity** — no `recapture_events` rows tagged with this skill in the last L days (default L=14), AND if the skill has >3 captured learning_rules, it has >0 firings in the last 30 days.

Demotion fires on any one of:
- A new failure event
- A new ALWAYS_BLOCK structural finding
- A recapture event implicating this skill

This is the structural addition over v7: **learning fidelity becomes a
first-class promotion input.**

### 4.4 The graduation gate

`_framework/autonomy/graduation_audit_gate.py` runs at the exact
promotion-decision point in `cmd_record_event`. Returns (block, reason).
On block:
- Records `audit_blocked_promote` event in `skill_autonomy_history`
- Files kanban task to owner with idempotency key
- Parks `consecutive_clean` at threshold so the next clean_run after the
  issue is fixed retries promotion
- Returns 0 from `cmd_record_event` (not an error; gate working)

(Same shape as the v7 implementation we built this session.)

### 4.5 Hard ceilings

Some actions are never autonomous regardless of skill level:
- `never-autonomous-send` per recipient
- New-contact first-message
- Anything in the `blacklist` portion of `email-access.md`

Hard ceilings are enforced at the send-guard layer (§6.4), not at the
autonomy gate.

---

## 5. SystemSentinelAgent — pure observability

### 5.1 Role and constraints

Sentinel is a first-class agent profile but with **read-only authority**:

- **Can:** read every profile's vault/db/state; watch logs; query DBs;
  file kanban tasks (tenant=`alert` / `audit` / `compliance` /
  `recapture`); compute metrics; write to `_state/events.db` (her own
  table).
- **Cannot:** send mail; modify any other profile's files; alter
  configs; change skills; mutate the learning corpus; mutate autonomy
  state; restart services. *Anything that changes state is forbidden.*

Code-enforced (sentinel's profile is in `hmail`'s permanent deny set;
her config.yaml has `agent.max_action_classes: []`).

### 5.2 Events table

`_state/events.db`:

```sql
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,          -- ISO8601 UTC
    kind        TEXT NOT NULL,          -- enum: cron_fire, skill_load, audit_finding,
                                        --   correction_captured, recapture_detected,
                                        --   autonomy_promote, autonomy_demote,
                                        --   audit_blocked_promote, send_attempt,
                                        --   send_blocked, operator_action,
                                        --   gateway_restart, ...
    actor       TEXT,                   -- profile or 'sentinel' or 'owner'
    target      TEXT,                   -- skill / cron / task id / etc.
    severity    TEXT,                   -- info | warn | critical
    payload     TEXT                    -- JSON
);

CREATE INDEX idx_ev_ts ON events(ts);
CREATE INDEX idx_ev_kind ON events(kind, ts);
CREATE INDEX idx_ev_actor ON events(actor, ts);
```

Every notable thing in the agency appends a row. Sentinel is the writer;
other subsystems publish via `events.append(kind, actor, target,
severity, payload)`. This becomes the single trend-queryable surface for
"what worked / what didn't" questions.

### 5.3 What Sentinel runs

Sentinel's cron set:

- **`learning-monitor`** (every 5m) — runs `recapture_detector` against
  any rules captured in the last cycle; appends to `events.db`; demotes
  skills + files kanban tasks per §3.5.
- **`drift-monitor`** (every 15m) — computes drift score per skill from
  the audit's last finding set; updates `_state/drift_scores.json`;
  alerts on score jumps above threshold.
- **`heartbeat-watch`** (every 5m) — checks `_state/heartbeats.db`; if
  any component's last_success_at is > 2x its expected interval,
  appends a `heartbeat_stale` event + files an alert.
- **`playbook-audit`** (Sundays 04:00) — full fleet audit; appends per-rule
  findings to `events.db`; files summary kanban task.
- **`event-rollup`** (hourly) — summarizes the last hour into a single
  `events_hourly_summary` row for fast trend queries.
- **`compliance-report`** (Sundays 06:00) — §3.7.

### 5.4 What Sentinel does NOT do

- Does not run the recapture *detector* — that runs at capture-time,
  inline. Sentinel just monitors recapture *events* and aggregates them.
- Does not gate promotions — that's `graduation_audit_gate.py` called
  from within `cmd_record_event`. Sentinel records the events but
  doesn't author the decision.
- Does not author skills, fix bugs, or take any kind of action.

If Sentinel notices something wrong, her only output is a kanban task to
the owner. She's the alarm, not the firefighter.

### 5.5 Persona stub

Sentinel's persona is laconic, factual, undramatic. She doesn't try to
sound friendly. She reports what's true; the owner decides what to do
about it. Default persona file `templates/profiles/system-sentinel/SOUL.md`
ships with this voice; deployments can edit but should resist making her
chatty.

---

## 6. Supporting seams

### 6.1 Verifier — typed completion, fail-closed

Same shape as v7 §16a. At `_framework/verifier/`:

- `verifier.py` — `check <task_id>` returns 0 if all criteria pass, 1 otherwise
- 10 registered criterion types (file_exists, file_contains, sql_query,
  kanban_status, learning_rule_recorded, etc. — see `verifier.py
  list-types`)
- Fail-closed: zero criteria → completion refused
- Wired into every kanban-completing skill via the `## Verifier criteria`
  section (scaffolds insert by default)

### 6.2 Injection scanner — paraphrase-don't-quote

Inherited from Hermes' `tools/cronjob_tools.py::_CRON_THREAT_PATTERNS`.
Scans assembled prompts (cron prompt + injected skill content) for
literal trigger phrases.

Framework adds: a `paraphrase-don't-quote` linter in the audit (the
`skill-injection-trigger` rule) that catches defensive content quoting
trigger phrases verbatim. (§P6.23 lesson from v7.)

### 6.3 Kanban — cross-profile channel

Same shape as v7 §17.10. Shared `_state/kanban.db`. Per-profile
`<profile>-kanban-processor` cron claims tasks where `assignee=<self>`.

**New in HermesAgency: two link types.**

- `blocks` — true ordering dependency (child must wait for parent)
- `tracks` — soft tracking (parent shows aggregate; doesn't gate)

This avoids the umbrella-deadlock pattern from v7 §P6.23. Requires a
small patch to `kanban_db.py` — schema migration + the promoter logic
checks only `blocks` parents. Patch goes to the post-update re-apply
hook list (or upstreamed to NousResearch as a PR — preferred path).

Tenant conventions (single source: `_framework/invariants.yaml`):
`dossier`, `hardware`, `red-team`, `cross-profile-msg`, `bizdev`,
`book-coaching`, `audit`, `audit-confirm`, `spec-review`, `alert`,
`compliance`, `recapture`.

### 6.4 Send-guard

Inherited from v7's `send_guard.py`. Wired into `hmail` as Guard 4.
Validates outbound mail against hard rules (deterministic checks).
Reads three-tier access list (`email-access.md`: white/grey/black).

Framework adds: `send-guard-rules.yaml` declares hard-rule validators in
a single config, generated from `learning_rules WHERE is_hard=1`.
Validators are added as one-line dict entries.

---

## 7. The six agent roles — templates

Each role ships with: persona stub, role description, starter skill
manifest (skills are stubs with frontmatter + structure; deployment
fills in content). Starter skills are FRAMEWORK content — clones inherit
them. Deployment-specific content goes in the deployment's profile dir.

### 7.1 ChiefOfStaffAgent

**Role:** Owner's single conversational surface AND the agency's single
outbound voice. Coordination, communication, real-time operations.
Multi-channel ingress (email, chat, Signal, Slack, dashboard chat tab)
normalizes here.

**Starter skills (framework-provided):**
- `owner-channels-ingress` — unified triage across email + chat + Signal
  + Slack + dashboard chat. Inbound from any channel becomes an "item to
  consider." (Replaces v7's narrower `inbox-management`.)
- `draft-composer` — drafts replies in the agency's voice. Receives
  inputs from specialist agents (via kanban results) and renders them
  as outbound mail.
- `send-orchestrator` — the canonical send path. Owns the send-guard
  (§6.4), the access-list, and the only outbound mailbox in the
  default deployment.
- `kanban-orchestrator` — claims her own tasks; spawns delegation
  tasks to specialists; collects their results back.
- `calendar-manager` — read/write calendar
- `morning-briefing` — daily summary
- `weekly-review` — Sunday recap
- `delegate-via-kanban` — route work to specialist agents
- `pipeline-watchdog` — observability over own pipeline

**Cadence:** Real-time. Most crons short-interval (2-5 min).

**Action class set:** draft-only (L1+), send-batched (L2+), send-single
(L3+). She's the only agent who declares send-* classes in the default.

### 7.2 KnowledgeBaseAgent

**Role:** Pure knowledge curator and IP-alignment validator. She *knows*
the agency's IP — frameworks, methods, prior decisions, established
positions, brand voice, prior content — and *validates* other agents'
and the owner's work product *against* that IP. She does not create
work product herself; that's CoS, BD, and WritingSupport's job. KB's
output is verdicts, annotations, and IP-aligned context, not artifacts.

This makes her structurally parallel to AnalystJudge: both **evaluate**
more than they **create**. The distinction:

- **KnowledgeBase asks:** "Does this match what we know / who we are?"
  (IP-aligned? doctrinally correct? consistent with our methodology?)
- **AnalystJudge asks:** "Will this hold up to scrutiny?"
  (adversarially robust? logically defensible? evidence-grounded?)

Both can flag the same artifact for different reasons; their findings
compose.

**Starter skills:**
- `ip-curator` — maintains the agency's IP corpus (frameworks,
  methods, doctrine) in the vault. Ingests new IP from CoS-routed
  inputs; classifies; preserves.
- `ip-alignment-check` — validates a draft artifact (email, post,
  proposal, workbook page) against the agency's IP. Returns
  `aligned` / `divergent: <reasons>` / `gap: <what's missing>`.
- `methodology-application-check` — verifies that a proposed action
  applies the right framework correctly (e.g., a coaching response
  applies the agency's coaching methodology).
- `prior-decision-search` — "have we decided something like this
  before?" Semantic search across the decision log.
- `meeting-evaluator` — evaluates meeting recordings/transcripts
  against the agency's standards for what good looks like.
- `quality-auditor` — second-tier verdict on work-product quality
  (composes with AnalystJudge's adversarial review).
- `kanban-verdict-publisher` — writes validation verdicts back as
  kanban task comments for CoS to act on. Does *not* publish work
  product — only verdicts/annotations on others' work.

**What KB does NOT do:**
- Draft emails, posts, proposals, or any outbound content
- Publish newsletters (that's WritingSupport drafts → CoS sends)
- Create workbook pages (WritingSupport)
- Author dossiers (AnalystJudge)
- Send anything externally (CoS)

If asked to "produce X," KB's correct response is "I don't produce
work — I evaluate what others produce. Route this to <appropriate
agent>." CoS-as-router knows this and shouldn't delegate creation to
KB in the first place.

**Cadence:** Mixed (5m kanban poll for validation requests, 6h
quality audits, weekly IP-corpus health reports).

**Action class set:** draft-only (L1+), structural-change (L4+) —
she edits the IP corpus.

**No mailbox in default.** All inputs arrive via kanban from CoS.

### 7.3 SystemSentinelAgent

**Role:** Watch. Per §5, no actions beyond filing kanban tasks.

**Starter skills:**
- `learning-monitor` (see §5.3)
- `drift-monitor`
- `heartbeat-watch`
- `playbook-audit`
- `event-rollup`
- `compliance-report`

**Cadence:** Frequent. Most crons every 5-15m. Compliance weekly.

**Action class set:** Empty. Sentinel does not declare action classes.

### 7.4 AnalystJudgeAgent

**Role:** Adversarial review, dossier, research, learning curation,
verifier authorship.

**Starter skills:**
- `red-team` — critique drafts/plans/decisions
- `dossier-builder` — biographical + contextual research (generalized
  from v7's `loriah-dossier`)
- `research` — vault/web research grounded in agency goals
- `prompt-injection-defense` — security analysis on inbound
- `learning-curation` — dedupe, contradict-check, hardness audit
- `verifier-criteria-author` — write typed criteria for new task types
- `graduation-check` — manual override path for autonomy review

**Cadence:** Project-paced. Hours to days per task. Crons infrequent.

**Action class set:** draft-only (L1+), structural-change (L4+) — she
edits the learning corpus.

### 7.5 BusinessDevelopmentAgent

**Role:** Lead-gen + opportunistic outreach + relationship building.
Expanded from v7's narrow CRM focus.

**Starter skills:**
- `prospect-research` — daily-news-driven target identification
- `opportunistic-outreach` — same-day outbound draft generation based
  on news/events
- `journalist-relationship` — earned-media relationship building (CoS
  drafts; this skill maintains state about journalists, beats, prior
  pitches)
- `podcast-host-relationship` — same shape for podcast booking
- `crm-sync` — CRM hygiene
- `weekly-opportunity-scan` — strategic pipeline summary

**Cadence:** Daily (news-driven) + weekly (strategic).

**Action class set:** draft-only (L1+), send-batched (L2+). She drafts;
CoS reviews and sends. (Same posture as v7 §17.7.)

### 7.6 WritingSupportAgent

**Role:** Author coaching + content production. Multi-author capable.
No external mailbox in default — author correspondence flows through
CoS, who routes per-author work to WritingSupport via kanban.

**Starter skills:**
- `book-coaching` — per-author coaching state, voice, project arc.
  Receives author-message kanban tasks from CoS; produces coaching
  responses for CoS to send.
- `manuscript-review` — feedback on author drafts (routed in by CoS)
- `workbook-drafting` — staff-facing instructional content (internal
  delivery — to vault, then surfaced to owner via CoS)
- `newsletter-drafting` — weekly newsletter authoring; hands the
  draft to CoS for send via `send-orchestrator`
- `multi-author-state` — maintains per-author project arcs, coaching
  histories, voice profiles in `context/writing-support/authors/`

**Cadence:** Per-author task pickup (5m via kanban) + weekly
newsletter cadence + ad-hoc workbook requests.

**Action class set:** draft-only (L1+), structural-change (L4+) — she
edits the multi-author state.

**No mailbox in default.** The per-author correspondence model is:
author emails `agency@<owner-domain>` (CoS's mailbox) → CoS recognizes
the author + context → delegates `tenant=book-coaching` task to
WritingSupport → WritingSupport drafts response in author-specific
voice → CoS reviews + sends as the agency. Authors see only the CoS
address; WritingSupport works invisibly behind.

This is a real architectural commitment: **per-author voice
calibration stays in WritingSupport; final outbound voice belongs to
CoS.** If a deployment wants direct author-to-WritingSupport mail
contact (e.g. AJ's existing libracrabill@gmail.com setup), override
via deployment.yaml — but the default ships single-mailbox.

---

## 8. Framework structure

### 8.1 Repo layout — target (v0.20+) and current (v0.17)

**Target layout** (v0.20 completes the flattening of `_framework/` into
the plugin package):

```
hermes-agency/                          (github.com/ajcrabill/hermes-agency, MIT)
├── README.md                           (public-facing pitch + 4-step install)
├── LICENSE                             (MIT)
├── CHANGELOG.md
├── pyproject.toml                      (declares hermes-agency-plugin entry point)
├── bootstrap.sh                        (curl-pipe installer; thin wrapper over pip)
├── docs/
│   ├── HERMES_AGENCY_SPEC.md           (this document)
│   ├── ARCHITECTURE.md                 (diagrams; cross-references §2)
│   ├── ROLES.md                        (the 6+ roles in §7)
│   ├── DEPLOYMENT.md                   (the 4-step install elaborated)
│   ├── LEARNING_LOOP.md                (§1.1 + §3 in conversational form)
│   ├── AUTONOMY.md                     (§4 ladder elaborated)
│   ├── SENTINEL.md                     (§5)
│   ├── INTEGRATIONS.md                 (Gmail / Signal / Slack / etc.)
│   └── examples/
│       └── minimal-deployment/         (smoke-test reference deployment)
├── hermes_agency_plugin/               THE plugin (= the whole codebase)
│   ├── plugin.yaml                     (Hermes plugin manifest)
│   ├── __init__.py                     (register(ctx))
│   ├── hooks.py                        (5 lifecycle-hook handlers)
│   ├── commands.py                     (/agency slash-command dispatch)
│   ├── context.py                      (profile + role resolver)
│   ├── constants.py                    (path constants, brand-agnostic)
│   ├── invariants.yaml                 (ALWAYS_BLOCK, tenants, action classes, providers)
│   ├── manifest.py                     (deployment.yaml schema + validator)
│   ├── learning/                       (§3 — the spine)
│   ├── autonomy/                       (§4)
│   ├── verifier/                       (§6.1)
│   ├── sentinel/                       (§5)
│   ├── send_guard/                     (§6.4)
│   ├── kanban/                         (§6.3 — the tracks-link shim into Hermes' kanban.db)
│   ├── audit/                          (audit-alignment + scheduled scripts)
│   ├── migration/                      (v7 → HermesAgency import)
│   ├── scaffolds/                      (scaffold-skill / scaffold-script / scaffold-profile)
│   ├── skills/                         (bundled skill catalog — registered with Hermes
│   │                                     via ctx.register_skill() on plugin load)
│   │   ├── _shared/                    (cross-role: development-playbook, prompt-injection-defense)
│   │   ├── chief-of-staff/             (CoS skills)
│   │   ├── knowledge-base/
│   │   ├── system-sentinel/
│   │   ├── analyst-judge/
│   │   ├── business-development/
│   │   ├── writing-support/
│   │   └── finance/
│   └── profiles/                       (bundled agent-identity templates — registered with
│                                         Hermes' agent registry via ctx.register_agent())
│       ├── chief-of-staff/             (SOUL.md.template + standards.md.template)
│       ├── knowledge-base/
│       ├── system-sentinel/
│       ├── analyst-judge/
│       ├── business-development/
│       ├── writing-support/
│       └── finance/
└── tests/
    ├── seams/                          (system seam tests)
    ├── audit/                          (audit-rule tests)
    └── e2e/                            (end-to-end smoke tests)
```

**Current layout (v0.17)** — mid-transition; same shape but with two
legacy paths preserved during the cleanup window:

- `_framework/<x>/` still holds the subsystems (learning, autonomy,
  verifier, sentinel, send_guard, kanban, audit, migration, scaffolds).
  v0.20 flattens this into `hermes_agency_plugin/<x>/`.
- `templates/profiles/<role>/` and `templates/scripts/` still hold
  profile + script templates as filesystem artifacts. v0.20 moves them
  into the plugin package and exposes them via Hermes' registries.
- `hermes_agency/cli.py` still implements the standalone `agency`
  command. v0.20 demotes this to a thin shim that invokes the plugin's
  slash-command handler for non-interactive use, and deletes the
  parallel-surface commands (`chat`, `panel`, etc. already gone in v0.15).
- `_framework/hermes_patches/` deprecated in v0.17; module deleted in
  v0.18.

### 8.2 Deployment layout (the customer's directory)

```
~/.agency/                              (the customer's deployment — NOT in framework repo)
├── deployment.yaml                     (owner, profiles enabled, paths, secrets refs)
├── framework-version.lock              (hermes-agency v0.1.0 — pinned)
├── framework-vault/                    (deployment-specific copies of system docs Sentinel watches over + anyone references)
│   ├── MASTER_PLAN.md
│   └── DEVELOPMENT_PLAYBOOK.md
├── profiles/                           (customer's actual content)
│   ├── <profile-1>/
│   │   ├── config.yaml                 (model, provider)
│   │   ├── auth.json                   (credentials)
│   │   ├── SOUL.md                     (who this agent IS — always-injected at skill-load)
│   │   ├── standards.md                (what this agent REFUSES to fall below — always-injected, per §2.5)
│   │   ├── skills/                     (mix of framework starters + customer-specific)
│   │   ├── scripts/                    (customer-specific cron scripts)
│   │   ├── cron/jobs.json
│   │   ├── state.db                    (Hermes engine state per profile)
│   │   ├── logs/
│   │   └── context/<profile>/          (vault — customer's content)
│   └── ...
├── _state/                             (shared, cross-profile — DEPRECATED, moves to ~/.hermes/agency-state/ in v0.20)
│   ├── kanban.db
│   ├── learning.db
│   ├── autonomy.db
│   ├── events.db
│   ├── heartbeats.db
│   └── drift_scores.json
└── _health/                            (DEPRECATED, moves to ~/.hermes/agency-state/_health/ in v0.20)
    ├── audits/                         (audit reports + scoreboard)
    ├── operator-actions.jsonl
    └── recapture-history.jsonl
```

**Target deployment layout (v0.20+)** — all agency state lives next
to Hermes' own state under `~/.hermes/`, no separate `~/.agency/`
world:

```
~/.hermes/                              (the engine's home, owned by Hermes)
├── ... Hermes' own state .db files ...
├── plugins/
│   └── hermes-agency/                  → symlink to installed plugin package
└── agency-state/                       (NEW in v0.20 — all HermesAgency state)
    ├── learning.db
    ├── autonomy.db
    ├── events.db
    ├── heartbeats.db
    ├── drift_scores.json
    ├── deployment.yaml                 (much slimmer — see §9)
    ├── framework-vault/                (deployment-specific copies of master plan + playbook)
    ├── vaults/                         (per-profile vaults — Goals.md / Values.md / etc.)
    │   ├── <profile_id>/
    │   │   ├── Goals.md
    │   │   ├── Values.md
    │   │   ├── Personal.md
    │   │   ├── Work.md
    │   │   ├── Client.md
    │   │   └── Soul.md                 (the *operator-edited* persona; bundled
    │   │                                 templates live inside the plugin package)
    │   └── ...
    ├── per-subject-state/              (per-author, per-coach, per-prospect scratchpads)
    └── _health/
        ├── audits/
        ├── operator-actions.jsonl
        └── recapture-history.jsonl
```

(Profiles themselves — identity templates, skill catalogs — live
inside the plugin package and get registered with Hermes' own agent
and skill registries on plugin load. The vault under
`agency-state/vaults/<id>/` holds the *operator-edited* content for
that profile.)

### 8.3 Brand-agnostic paths

Every path in the framework derives from constants in
`hermes_agency_plugin/constants.py`. The owner's chosen agent names
(e.g., "Loriah" for CoS, "Lynda" for Analyst) live ONLY in
deployment-edited files — never in plugin paths, never in plist
labels, never in env var names.

Plist labels: `com.hermes-agency.cron.<profile-id>.plist`. The
`profile-id` is the deployment's chosen name; the rest is plugin-fixed.

### 8.4 Two-tier file ownership rule

Every file in `hermes_agency_plugin/` (or its `_framework/` predecessor
during the v0.17–v0.19 transition) carries a header:
```python
# PLUGIN — owned by HermesAgency. Do not modify in a deployment;
# customizations belong in ~/.hermes/agency-state/ (data) or
# in deployment.yaml (configuration).
```

Every file in a deployment's vault (`~/.hermes/agency-state/vaults/<id>/`)
is owner-edited; plugin upgrades will not touch operator content. The
plugin treats operator content as input, never as something to rewrite.

The audit (§10) checks that plugin files don't contain literal owner
names, mail addresses, or contact references — pure plugin code,
content-empty.

---

## 9. Deployment manifest

`~/.agency/deployment.yaml`:

```yaml
# HermesAgency deployment manifest
deployment:
  owner:            aj-crabill
  org_name:         "AJ Crabill — Effective Boards"
  primary_email:    ajcrabill7@gmail.com
  timezone:         America/Chicago
  framework_version: 0.1.0

# Which roles are active in this deployment.
# Required: chief-of-staff, knowledge-base, system-sentinel.
# Optional: analyst-judge, business-development, writing-support.
# Custom: define your own role (advanced).
profiles:

  - id:           loriah                # the name THIS owner gives this role
    role:         chief-of-staff        # framework role from §7
    persona_file: identities/chief-of-staff.md     # SOUL.md — who CoS is
    # standards.md lives at profiles/<id>/standards.md by convention (per §2.5)
    email:        loriahcrabill@gmail.com
    starter_skills:                     # which framework-provided starters to enable
      - inbox-management
      - draft-composer
      - kanban-orchestrator
      - calendar-manager
      - morning-briefing
      - weekly-review
      - delegate-via-kanban
      - pipeline-watchdog

  - id:           lynda
    role:         analyst-judge
    persona_file: identities/analyst-judge.md
    email:        null                  # internal-only
    starter_skills:
      - red-team
      - dossier-builder
      - research
      - prompt-injection-defense
      - learning-curation
      - verifier-criteria-author
      - graduation-check

  - id:           esby
    role:         knowledge-base
    persona_file: identities/knowledge-base.md
    email:        null                    # default: single-mailbox via CoS
    starter_skills:
      - librarian
      - quality-auditor
      - meeting-evaluator
      - knowledge-router
      - archive-search
      - kanban-result-publisher

  - id:           sentinel               # SHOULD be left as 'sentinel' in v0.1
    role:         system-sentinel
    persona_file: identities/system-sentinel.md
    # Sentinel's standards.md is short — it references the master plan + playbook as her canonical standards
    email:        null
    starter_skills:                      # all are framework-required for Sentinel
      - learning-monitor
      - drift-monitor
      - heartbeat-watch
      - playbook-audit
      - event-rollup
      - compliance-report

  - id:           devon
    role:         business-development
    persona_file: identities/business-development.md
    email:        null                   # CoS drafts external mail
    starter_skills:
      - prospect-research
      - opportunistic-outreach
      - journalist-relationship
      - podcast-host-relationship
      - crm-sync
      - weekly-opportunity-scan

  - id:           libra
    role:         writing-support
    persona_file: identities/writing-support.md
    email:        null                    # default: single-mailbox via CoS
    starter_skills:
      - book-coaching
      - manuscript-review
      - workbook-drafting
      - newsletter-drafting
      - multi-author-state

  # — Example of adding a custom role (FinanceAgent etc.) —
  # Uncomment + customize when expanding the deployment.
  # The role must exist either in _framework/roles/ or in
  # ~/.agency/custom-roles/. No code change needed to load it.
  #
  # - id:           finance
  #   role:         finance               # custom role
  #   persona_file: identities/finance.md
  #   # standards.md lives at profiles/finance/standards.md by convention
  #   email:        null
  #   starter_skills:
  #     - cash-flow-tracker
  #     - burn-rate-monitor
  #     - vendor-research

# Model / provider config (cascade: profile.config.yaml > deployment > framework default)
# Framework is vendor-neutral. Any OpenAI-compatible endpoint works.
# The deployment picks. Example below shows the structure; substitute your
# preferred provider.
defaults:
  model:    <your-model-id>             # whatever model id your provider expects
  provider: <your-provider-id>          # any OpenAI-compatible: local, hosted, mixed
  base_url: <your-endpoint>             # http://localhost:11434/v1 for local Ollama,
                                        # or https://your-provider.example/v1
  fallback_providers:                   # optional cascade if primary fails
    - provider: <fallback-provider-id>
      model:    <fallback-model-id>
      base_url: <fallback-endpoint>

# Credentials reference (NEVER inline the values — Keychain or .env only)
# Add one entry per provider you actually use. The framework doesn't care
# which providers you choose.
credentials:
  <provider-id>: keychain:<keychain-entry-name>   # repeat per provider in use

# Send-guard access list location
email_access_file: profiles/<cos-profile-id>/scripts/learning-system/email-access.md
```

### 9.1 Validation

`_framework/manifest.py::validate(yaml_path)` enforces:
- All required roles present (CoS + KnowledgeBase + Sentinel)
- Profile IDs unique
- Persona files exist
- Starter skills exist in framework templates
- Provider in `_framework/invariants.yaml::valid_providers`
- Credentials references resolvable
- No inline secrets

Run on every `agency init`, `agency upgrade`, and as a first check in the
boot sequence.

---

## 10. Playbook + scaffolds + audit (the closed loop)

### 10.1 Playbook v2.0.0 (framework-generic)

Same shape as v7's v1.1.0 playbook but with all brand-references removed.
Path: `hermes-agency/DEVELOPMENT_PLAYBOOK.md`.

Sections preserved:
- §0 When this fires
- §1 The five system seams (learning emphasized as the spine)
- §2 Skill anatomy
- §3 Verifier criterion types
- §4 Prompt-injection defense template
- §5 Script anatomy
- §5.5 Artifact lifecycle (T1/T2/T3 tiered creation)
- §6 Profile creation (refs §17.0 dynamic discovery)
- §7 Cross-profile work (kanban tenants)
- §8 Path conventions
- §9 Audit rules (7-category taxonomy)
- §9.5 Audit cadence + graduation gate
- §10 Versioning + change log
- §11 Deferred items

Change log: `v2.0.0 (HermesAgency extraction) — extracted from
ajcrabill's v7 deployment, generalized for framework distribution.`

### 10.2 Scaffolds

Same shape as v7. Path-constant-aware. Read `deployment.yaml` for owner
values. Output is brand-agnostic frame + placeholder content for
deployment to fill.

- `scaffold-skill.py --role <role> --name <name>` — emits SKILL.md with
  proper frontmatter (incl. autonomy block matching role's
  default-action-classes)
- `scaffold-script.py --profile <id> --name <name>`
- `scaffold-profile.py --role <role> --id <id>` — adds a new profile to
  the deployment
- `scaffold-deployment.py` — the `agency init` wizard

### 10.3 Audit

Same shape as v7's audit. Per-rule history scoreboard. All
ALWAYS_BLOCK rules from v7 plus new ones:

- `learning-loop-broken` — skill has >3 captured rules but 0 firings in
  30 days (NEW; ALWAYS_BLOCK)
- `skill-no-supervised-learning` — promoted from warn to ALWAYS_BLOCK
  for graduation gate (NEW)
- `recapture-implicates-skill` — recapture_events table has a row in
  the last 14 days tagged with this skill (NEW; ALWAYS_BLOCK for
  graduation gate; warn for general audit)

The audit reads invariants from `_framework/invariants.yaml` (single
source) — no more 3-way duplication of ALWAYS_BLOCK.

---

## 11. Operator surface

### 11.1 Control panel

Read + write operator UI at `https://<machine>:9118/control-panel`.
Single-tenant per machine. Auth via email-OTP (same as v7 §P6.21).

Sections:
- **Learning loop health** (top of page — the central promise's status)
  - Rules captured this week
  - Recapture events (red if >0 — the loop is broken)
  - Top-firing rules
  - Skills with broken learning (>3 rules, 0 firings)
- **Per-agent status** (one card per profile)
  - Heartbeat, cron summary, autonomy levels, recent firings
  - Per-cron action buttons (pause/resume/run/clear) as v7 v2
- **Sentinel events feed** (live tail from events.db)
- **Audit summary** (latest run, trend)
- **Global controls** (kanban dispatch, unblock, service restart)

### 11.2 Hermes dashboard plugin

Same plugin shape as v7 — kanban + control-panel plugins ship in
`hermes-agency/dashboard-plugins/` (separate from upstream Hermes;
installed into the engine post-clone via post-install hook).

### 11.3 In-Hermes slash command — the primary surface

The supervisory surface lives inside `hermes` as the `/agency`
slash command, registered by the plugin via
`ctx.register_command("agency", ...)`:

```
/agency status                  # deployment health + Hermes detection
/agency next                    # actionable next-steps
/agency systems                 # 7-system integration inventory
/agency capture "<correction>"  # capture a learning correction
/agency learn list [N]          # list recent learning rules
/agency audit                   # run the alignment audit
/agency setup                   # migration-or-clean-install interview (v0.19+)
/agency help                    # subcommand listing
```

Operators don't leave Hermes to run agency operations. The owner-
agency interface model (§2.3) holds: one face for the owner, one
face for the world, both inside `hermes`.

### 11.4 Shell-side `agency` command — thin shim for non-interactive use

A standalone shell-side `agency` command exists for contexts where
a slash command isn't available — cron-fired scripts, CI pipelines,
non-interactive automation:

```
agency status              # mirror of /agency status
agency capture "..."       # mirror of /agency capture
agency audit               # mirror of /agency audit
agency migrate v7 ...      # the v7-import operation
agency promote <skill>     # force-promote (with audit gate)
agency demote <skill>      # force-demote
```

This shim must not contain operator-facing UX that competes with
`hermes` (no `agency chat`, no `agency panel` as a primary surface,
no `agency init` wizard). The v0.15 plugin-discipline rule (§1.4)
holds: `hermes` is the runtime, always.

### 11.5 Control panel — read-only diagnostic UI

The plugin's optional control panel (at `localhost:9118/control-panel`)
remains a read-only diagnostic surface — not the operator's daily UI.
Use it for at-a-glance learning loop health, sentinel feed inspection,
and audit summaries. Daily work happens in `hermes`.

---

## 12. Done = / Out of scope for v0.1

### 12.1 Done = (the v0.1 acceptance bar)

A fresh, blank machine can:

1. `pip install hermes-agency` (or `git clone` + `make install`)
2. `agency init` → answer wizard → deployment created at `~/.agency/`
3. `agency status` → all six profiles reporting healthy heartbeats,
   Sentinel watching, learning DB initialized empty
4. `agency capture "test correction"` → rule appears in
   `_state/learning.db`, embedded, recapture-checked
5. A kanban task created via `hermes kanban create --assignee <id>` →
   processor picks it up within 5m → verifier checks (no criteria → blocks
   with explanatory comment) → ALWAYS_BLOCK audit gate runs (clean for
   starter skills) → task moves to expected state
6. Re-capture detection works: capture the same correction twice →
   `recapture_events` row appears → Sentinel files an alert kanban task
   → responsible skill demotes
7. Control panel at port 9118 shows the deployment with learning-loop
   health at the top
8. Public docs in the repo are sufficient for a new owner to read
   README → ARCHITECTURE → DEPLOYMENT and get to step 1 above

### 12.2 Out of scope for v0.1 (deferred to v0.2+)

- Owner content migration (AJ's specific skills, learning rules,
  dossiers — this is the post-v0.1 migration project, not v0.1 itself)
- Cost / token attribution per skill
- Multi-machine deployment
- Quarterly deep semantic audit pass
- Anything not explicitly in §12.1

---

## 13. Migration plan — AJ as first customer

Phased, post-v0.1. v7 stays authoritative throughout. Timeline:
~4-6 months.

### 13.1 Pre-migration (weeks 1-2 after v0.1 ships)

- Stand up `~/.agency/` on AJ's machine alongside v7
- Run `agency init` with AJ's role-naming preferences (loriah / lynda
  / esby / sentinel / devon / libra)
- Validate v0.1 end-to-end: send a correction, watch it propagate,
  re-correct to test recapture detection, verify the full chain works
- This is the **learning-loop validation phase** — nothing else gets
  migrated until the spine is provably solid

### 13.2 Phase 1 (month 1) — CoS migration

- Port `loriah-inbox-management` (the 135-rule skill) into
  `~/.agency/profiles/loriah/skills/`
- Migrate the 135 inbox-management rules with re-tagging pass
- Dual-run email triage: v7 fires, .agency shadow-fires; compare
  classifications for divergence
- Cut over inbox triage when shadow runs match v7 for 7 consecutive
  days

### 13.3 Phase 2 (month 2) — Lynda + autonomy + audit migration

- Port autonomy_engine state from v7's `loriah.db.skill_autonomy` →
  `~/.agency/_state/autonomy.db`
- Port the audit history from v7's `_health/audits/` → `~/.agency/_health/audits/`
- Migrate red-team + dossier-builder + learning-curation skills
- Validate graduation gate fires on .agency the same way it does on v7

### 13.4 Phase 3 (month 3) — Esby + Sentinel + learning corpus

- Port the remaining 58 learning_rules (post-WS1-carve-out) with
  re-tagging
- Migrate Esby's librarian + quality-auditor + meeting-evaluator skills
- Sentinel takes over from v7's standalone watchdog scripts

### 13.5 Phase 4 (months 4-5) — Devon expansion + Libra expansion

- Devon: bring forward the existing 5 BD skills, then expand into the
  new functions (news-driven outreach, journalist + podcast
  relationship building) directly in .agency (not in v7)
- Libra: bring forward book-coaching, then expand to multi-author +
  staff workbooks + weekly newsletter directly in .agency

### 13.6 Cutover (month 6)

- Final delta sync (any v7 state not yet in agency-state)
- AJ flips authoritative bit
- v7 archived (frozen, read-only) for 6 months as a fallback
- After 6 months stable on the new install, v7 deleted

### 13.7 Plugin-integration closure plan (v0.18 → v0.22)

v0.17.0 corrected the architectural shape — HermesAgency is now a
real Hermes plugin with all 7 reliability systems wired via the
documented plugin API. The remaining work is structural cleanup
to bring the codebase fully in line with "plugin-from-the-start"
design. Each release below is a release-sized chunk of real work.

**v0.18.0 — Verifier enforcement + deprecated-module removal**

- The post_tool_call hook in the plugin currently records tool
  completions to events.db (observation). v0.18 adds the
  `transform_tool_result` hook: for skill-bound tool calls, run
  the skill's `verifier:` block (§6.1) against the result; on
  failure, rewrite the result into an actionable error string so
  the LLM sees a clear "this output failed verifier X — fix Y"
  message rather than a silent pass.
- Delete `_framework/hermes_patches/` (deprecated in v0.17;
  REGISTRY already empty; one-release grace window expires).
- Delete the 4 `@pytest.mark.skip`-ed text-patch tests.

Acceptance: a skill whose verifier asserts `file_contains` on a
generated draft sees the failure surfaced as a tool-result error
to the LLM, not a silent completion. The verifier gate is
load-bearing inside Hermes' execution.

**v0.19.0 — `/agency setup` interactive interview (in-Hermes)**

The v0.17 `/agency setup` stub becomes a real conversational
flow. On fresh deployments (no `~/.hermes/agency-state/.configured`
marker), CoS opens with:

> "Is this a fresh install or are you migrating from a prior
> deployment? If migrating, where is your v7 home directory? If
> fresh, I have ~10 minutes of setup questions to learn who you
> are and what you're working on."

The migration path invokes `migrate_v7_full(<path>)` and reports
what landed. The clean-install path conducts an interview that
writes Goals.md, Values.md, Personal.md, Work.md, Clients.md,
and (per-profile) SOUL refinements. Either path ends by writing
the `.configured` marker so the prompt doesn't re-fire.

The bash `agency init` wizard is deleted (was only a v0.1–v0.18
vestige; bootstrap.sh creates the minimum skeleton needed for
Hermes to load the plugin, then `hermes` + `/agency setup`
handles everything else).

Acceptance: a fresh install on a clean machine, after the 2-step
curl-pipe install of Hermes + HermesAgency, is fully configured
through a `hermes` conversation alone. No second bash wizard, no
yaml editing, no operator-side file fiddling.

**v0.20.0 — Structural rename + parallel-state collapse**

- `_framework/<x>/` → `hermes_agency_plugin/<x>/` (subsystems
  move inside the plugin package; the `_framework` prefix retires).
- `~/.agency/_state/*.db` → `~/.hermes/agency-state/<x>.db`
  (state lives next to Hermes' own DBs; no separate `~/.agency/`
  world).
- `~/.agency/profiles/` → registered via `ctx.register_agent(...)`
  on plugin load (profiles become first-class Hermes agents).
- `~/.agency/_health/` → `~/.hermes/agency-state/_health/`.
- Deployment.yaml shrinks to a minimum (just operator identity +
  profile activation overrides + integration credential refs).
  Most of what used to live there moves to Hermes' own config
  (provider, model, etc.).
- Standalone `agency` CLI demoted to a thin shim that invokes
  the plugin's `/agency` handler for non-interactive contexts.
  Any operator-facing UX-rich CLI commands (`chat`, `panel`)
  removed entirely.
- Migration helper: v0.20 ships a one-shot
  `agency migrate-to-v020` command that moves `~/.agency/`
  contents into `~/.hermes/agency-state/` and registers profiles
  with Hermes. Idempotent. After this lands, all subsequent
  installs are "plugin from the start."

Acceptance: a fresh Hermes install with HermesAgency v0.20+ has
zero files outside `~/.hermes/`. `agency status` reports state
location as `~/.hermes/agency-state/`. The plugin discipline rule
(§1.4) is structurally enforceable: any new code adding
`~/.agency/` paths fails the audit.

**v0.21.0 — agentskills.io conformance pass**

The plugin's bundled skill catalog (`hermes_agency_plugin/skills/`)
is reviewed against the [agentskills.io](https://agentskills.io)
open standard the Hermes README points at. Schema differences
get reconciled; conformance becomes a CI check. Skills become
portable to any agent runtime that supports the standard.

Acceptance: a skill picked from `hermes_agency_plugin/skills/`
loads cleanly under both Hermes and any other agentskills.io-
compatible runtime, without modification.

**v0.22.0 — PyPI publication + entry-point install**

HermesAgency publishes to PyPI as `hermes-agency`. The package
declares a Hermes plugin entry point in `pyproject.toml`:

```toml
[project.entry-points."hermes.plugins"]
hermes-agency = "hermes_agency_plugin:register"
```

Hermes' `PluginManager` discovers pip-installed plugins via this
group. bootstrap.sh becomes a 5-line wrapper:

```bash
#!/bin/bash
set -euo pipefail
command -v hermes >/dev/null || { echo "install Hermes first"; exit 1; }
pip install hermes-agency
echo "✓ HermesAgency installed; run: hermes"
```

Acceptance: a user can install everything with two commands:

```bash
curl -fsSL https://.../hermes-install.sh | bash
pip install hermes-agency
```

And then `hermes` works with the plugin auto-discovered.

After v0.22.0, HermesAgency is fully what the spec said it would
be: a Hermes plugin (not a parallel framework), pip-installable
(not git-clone-bootstrap), discovered via entry points (not
filesystem convention), with all state living in `~/.hermes/`
(not a separate `~/.agency/`), conversational setup inside
`hermes` (not a bash wizard), and skills conformant to an open
standard (not framework-proprietary). The structural drift from
v0.1 → v0.16 is fully repaid.

---

## 14. Decisions still open

These need AJ's call before v0.1 build starts:

1. **Repo name** — `hermes-agency` (proposed) or `HermesAgency` casing?
   GitHub URL slug matters for SEO.
2. **Sentinel's name** — kept generic "sentinel" in the spec. AJ may
   want a deployment-specific name (like Loriah/Lynda/etc.).
3. **Patches to Hermes** — what's the upstream PR strategy? Three
   patches we'd want upstream (HERMES_INGATEWAY_CRON flag, two
   kanban link types, learning-rule injection hooks). The
   `kanban_patches/` directory exists as a fallback if upstream
   declines, but I'd file PRs first.
4. **Install mechanism** — `pip install hermes-agency` or
   `git clone` + script? Probably both, with pip as primary once
   stable.
5. **Versioning cadence** — semver. Major bumps for breaking deployment
   changes (manifest schema changes). Minor for new starter skills /
   new audit rules. Patch for bug fixes.
6. **What happens to the v0.1 spec doc** when v0.1 ships? Move to
   `hermes-agency/HERMES_AGENCY_SPEC.md` (with version updates), keep
   this draft in v7 vault as a historical artifact.

---

## 15. Build sequence

Once §14 decisions are made, v0.1 ships in this order:

- **Week 1** — framework skeleton (directory layout, constants.py,
  invariants.yaml, manifest schema + validator, deployment.yaml.template).
  GitHub repo created. README + LICENSE.
- **Week 2** — learning subsystem (§3) end-to-end. The spine first.
  Including recapture detector + tests.
- **Week 3** — autonomy ladder (§4) + verifier (§6.1) + graduation gate
  (§4.4) + send-guard (§6.4). All composing around the spine.
- **Week 4** — Sentinel (§5) infrastructure + events.db + the cron set
  she runs. Audit (§10.3) ports from v7 with single-source-of-truth
  invariants.
- **Week 5** — six role templates (§7) with starter skills as stubs.
  Reference deployment in `examples/`. End-to-end smoke test.
- **Week 6** — `agency init` wizard. CLI. Control panel port. Public
  documentation pass.

v0.1 ship at end of Week 6. Build is ~6 weeks, not 3 as I initially
estimated — the proper learning-loop-as-spine framing made me realize
how much depends on getting the spine right before the supporting seams.

---

## Appendix A — Components borrowed from prior projects (dCoS + agent-core)

Reviewed `github.com/ajcrabill/dCoS` and `github.com/ajcrabill/agent-core`
for components worth lifting into HermesAgency. AJ specifically called
out the **deep interview setup pattern** plus simpler fast-startup
alternatives. Both repos contain mature thinking on adjacent problems;
this appendix lists what we're explicitly bringing forward and what
we're leaving for v0.2+.

### A.1 In v0.1 — explicit adoption

1. **Three-tier setup wizard.** (agent-core ARCHITECTURE.md §Setup
   Wizard + ROADMAP Sprint 8.) The fast/slow startup pattern AJ wanted:
   - **Tier 1 (5-10 min) "Just defaults"** — required only: owner name,
     primary email, model/provider, storage backend, vault path. Boots a
     working deployment with sensible defaults across all 6 agents.
   - **Tier 2 (15-30 min) "Recommended"** — Gmail/Calendar OAuth,
     OpenBrain ingest sources (if any), daily-digest schedule, ingress
     channel configuration (which of email/Signal/Slack/chat the owner
     wants for talking to CoS).
   - **Tier 3 (45-60 min) "Power user / deep interview"** — content-
     creation skill definitions per role, IP-corpus bulk import (for KB),
     action-policy overrides per agent, multi-identity (multiple
     mailboxes if not single-mailbox default), skill catalog selection,
     persona voice calibration via exemplar capture.

   Wizard lands under `_framework/ops/init/` and runs via
   `agency init --tier {1|2|3}`. Tier 1 is non-interactive
   (sensible defaults). Tier 2 is mostly y/n + paste-key. Tier 3 is a
   real interview — the agent asks the owner about their work, their
   IP, their preferred voice, captures exemplars, and uses that input
   to calibrate the starter skills.

   This is the **deep interview at setup AJ was proud of in dCoS,
   formalized as a three-tier choice** so simpler/faster paths still
   work.

2. **Goal-directed operation principle.** (agent-core core principle.)
   Every inbound (email, chat, peer message, kanban task) spawns an
   obligation. Every obligation has testable completion criteria. Every
   autonomous action traces back to an obligation. Agents loop: while
   there are active agent-owned obligations, develop a plan or execute
   the next plan step. **Sleep only when nothing is actionable.**

   This is sharper than v7's cron-driven model. Crons in HermesAgency
   become the *clock* (they fire the agent loop); obligations become
   the *unit of work* (what the agent does in each iteration). Worth
   making this an explicit architectural commitment in §2 — added as
   a new commitment.

3. **State lives in code, not in instructions.** (agent-core core
   principle.) Learning rules, obligations, peer messages get *injected
   into the model's context by code*, not by "remember to read this"
   rules. Already aligned with v7 §7 WS2 / playbook §1 first seam;
   agent-core's phrasing is more crisp. Adopt the phrasing for the
   public framework pitch.

4. **Markdown projection — vault is the human projection, DB is the
   source of truth.** (agent-core ARCHITECTURE §Storage.) Any write to
   operational tables regenerates the corresponding `.md` files in the
   vault. The DB is canonical; the vault is human-readable derived.
   This solves the v7 "vault and DB drift" problem we hit multiple
   times. Add `_framework/state/markdown_projector.py` that listens for
   table writes (or runs periodically) and regenerates the vault md.

5. **Three orthogonal action classes — Autonomous / Gated / Forbidden.**
   (agent-core action policy.) Orthogonal to the L1-L5 autonomy ladder.
   - **Autonomous:** read, write-internal, OB updates, cross-agent
     messages, calendar reads, ingest pipelines, exemplar capture
   - **Gated (one-click human confirmation):** send external email,
     publish content, create external calendar invite, modify People
     notes, install new skill from catalog
   - **Forbidden:** secret access, financial actions, modifying safety
     policies

   v7's L1-L5 ladder tells WHEN a skill can take action; agent-core's
   class taxonomy tells WHICH actions need confirmation regardless of
   skill level. Both compose. The autonomy gate checks both: (1)
   action class allows; (2) skill level meets the action class's
   minimum.

6. **Two-tier quality auditor + auto-undelegation.** (agent-core
   `agent_core.quality`.) The verifier we already built handles
   pass/fail; agent-core's two-tier auditor also SCORES delivered work
   on a continuous scale, and *automatically* undelegates work to a
   lower-trust agent (or back to owner) when scores drop. Maps to v7's
   demotion-on-failure but more granular. Adopt for HermesAgency
   `_framework/quality/` — composes with the existing verifier (§6.1).

7. **OpenWebUI as the chat surface.** (agent-core architectural
   commitment, "best-in-class tools at the edges.") Don't reinvent
   chat. The owner-channels-ingress skill (§7.1) accepts chat through
   OpenWebUI as one of its inputs. ObligationBoard plugin lets the
   agent manipulate tasks from inside chat.

8. **Bring-your-own inference — vendor-neutral by design.**
   (agent-core principle, made explicit.) The framework speaks
   OpenAI-compatible API and makes no assumptions about which model
   or which provider sits behind it. Local-only, hosted-only, mixed,
   single-vendor, multi-vendor — all are valid deployment choices.
   The framework code never names a vendor; vendor identity lives in
   the deployment's `deployment.yaml` and is invisible to every
   skill, audit rule, scaffold, and Sentinel check. **This is a
   first-class architectural commitment, not a configuration
   convenience — see §1.3 below.**

### A.2 Deferred to v0.2+ (real value, not v0.1 scope)

9. **Synthetic edge-case battery.** (agent-core ROADMAP Sprint 11.5 +
   §3 supervised learning.) "Threshold-gated synthetic edge-case
   battery generates hard cases from your accumulated exemplars —
   collapsing weeks of 'wait for the edge case to show up' into days."
   This is a learning-acceleration mechanism: once a skill has N
   exemplars, generate synthetic variations + adversarial edge cases
   and run them through the skill to find gaps before production
   does. Add to v0.2.

10. **Mesh layer — native agent-to-agent collaboration across
    deployments.** (agent-core Sprint 6.) Postgres-backed (or SQLite
    for personal-scale), HTTP+JSON wire protocol, ed25519 peer auth,
    at-least-once delivery, idempotent receive, explicit ack on
    processing. AJ said single-machine for v0.1; mesh is the future
    multi-machine / multi-deployment story. Defer until there's a
    second deployment that wants to talk to AJ's.

11. **ObligationBoard 4-column kanban model.** (agent-core +
    OpenWebUI plugin.) Simpler than v7's 7-state kanban
    (archived/blocked/done/ready/running/todo/triage). 4 columns:
    Inbox / In Progress / Waiting / Done. Worth considering for the
    HermesAgency CoS-facing kanban view (specialist agents still use
    the richer state machine internally). Defer to v0.2 — adds UI
    surface area without changing the substrate.

12. **Content-creation pipeline with exemplars + iterations +
    diff-extractor + calibration.** (agent-core Sprint 5c.) The
    "point at exemplars, iterate from raw input, agent learns to
    deliver reliably" pattern. This is the supervised-learning
    accelerator for content production specifically (drafts, posts,
    newsletters). HermesAgency v0.1 has the learning loop generic
    across all skills; content-creation gets a specialized pipeline
    in v0.2 because content is where exemplar→delivery diffs are
    most informative.

13. **MkDocs Material for read-only knowledge publishing.** (iKB-agent
    surface.) If KB's IP corpus warrants a published surface for
    collaborators to read, MkDocs is the proven choice. v0.1 keeps
    everything in the vault; v0.2 adds the publish surface if there's
    a real audience.

14. **Identity layer for multi-tenant deployments.** (agent-core
    `agent_core.identity`.) Single-deployment-single-owner is fine
    for v0.1. Multi-tenant (multiple owners on one deployment) is
    real engineering work — defer indefinitely or until there's
    demand.

### A.3 Considered and rejected for HermesAgency

- **Hermes engine fork.** agent-core forks Hermes at
  `packages/hermes/` and patches in-tree. AJ's explicit call for
  HermesAgency: no fork. Use post-update reapply hook pattern + file
  upstream PRs for patches we need. (§14 decision 2.)
- **Postgres + pgvector as primary backend.** iKB-agent defaults to
  this. HermesAgency stays SQLite for v0.1 (single-machine, smaller
  scale, simpler ops). Add pgvector for semantic search of KB's IP
  corpus + recapture detector in v0.2 if needed.

### A.4 What's NOT borrowed from dCoS specifically

The dCoS repo is an older, narrower implementation that agent-core
generalizes. We're stealing the *patterns* (interview wizard,
obligation-tracking, observe-suggest-respect-autonomy) but not the
*code* (dCoS is pre-agent-core; the implementation has been
superseded). The `examples/minimal_config.yaml` shape is worth
referencing when designing HermesAgency's `deployment.yaml` schema
(§9) — both have the "configure what matters, default the rest"
shape.

---

## 16. Change log

- **0.1.0-spec.0 (2026-05-23 PM)** — initial draft. Foregrounds learning
  loop as the spine; six agents named per AJ's call; expanded BD and
  Writing per AJ's roadmap; Sentinel as first-class read-only agent;
  three-input autonomy promotion.
- **0.1.0-spec.1 (2026-05-23 PM)** — single-mailbox default. Only CoS has
  an outbound mailbox; all other agents default to `email: null`. New
  §2.3 "Owner-agency interface model — one face" codifies the
  commitment: agency is one face to the owner (CoS) and one face to
  the world (CoS). Multi-channel ingress (email/chat/Signal/Slack)
  normalizes to CoS. Specialists draft → CoS sends. Per-author Writing
  workflow updated accordingly. New §2.4 "Adding new agents" makes
  N-role expansion (e.g. future FinanceAgent) a first-class design
  property, not an afterthought; framework supports any number of
  roles, on-disk discovery, role keyword extension. CoS section
  (§7.1) restructured around `owner-channels-ingress` +
  `send-orchestrator`. KnowledgeBase (§7.2) and Writing (§7.6)
  sections updated to remove external mailbox defaults; both now
  route through CoS via kanban.
- **0.1.0-spec.2 (2026-05-23 PM)** — borrowed-components pass after
  AJ's directive to review dCoS + agent-core repos. §7.2 KB role
  corrected to pure curator/IP-validator (parallels AnalystJudge in
  evaluating-not-creating shape); starter skills restructured around
  IP corpus + alignment-check + verdict-publisher; explicit list of
  what KB does NOT do. New Appendix A "Components borrowed from
  prior projects" documents 8 v0.1 adoptions (three-tier setup
  wizard, goal-directed operation, state-in-code, markdown
  projection, action class taxonomy, two-tier quality auditor,
  OpenWebUI, BYO inference) + 6 v0.2+ deferred (synthetic edge-case
  battery, mesh layer, ObligationBoard 4-col view, content-creation
  pipeline, MkDocs publish, identity layer) + 2 considered-and-
  rejected (Hermes fork, Postgres-primary). The three-tier setup
  wizard (Tier 1 fast / Tier 2 recommended / Tier 3 deep interview)
  is the explicit fast/slow startup pattern AJ asked for.
- **0.1.0-spec.6 (2026-05-23 PM)** — final simplification per AJ:
  single doc per agent, consistent filename `standards.md`. Same
  filename for every role; CONTENT varies. Sentinel's `standards.md`
  is short and references the master plan + playbook by content (no
  multi-document loading machinery needed). Eliminated:
  `standards_files:` field from deployment.yaml (now by-convention
  loaded from `profiles/<id>/standards.md`); the `standards/`
  directory in the deployment layout (files live alongside SOUL.md
  in each profile root); per-role template names like
  `stewardship.md.template` / `accuracy.md.template` / `rigor.md.template`
  / `craft.md.template` / `voice.md.template` (all just
  `standards.md.template` now). Result: one consistent rule —
  every profile carries `SOUL.md` + `standards.md` at its root,
  both always-injected, no per-role naming convention to remember.

- **0.1.0-spec.5 (2026-05-23 PM)** — standards-source-of-truth
  refinement after AJ note that it can be multi-document AND can
  refer to shared system docs rather than always being a derived
  role-file. §2.5 updated: standards layer is now "plural" — one or
  more documents per agent. Manifest schema in §9 changes
  `standards_file:` (singular string) → `standards_files:` (list).
  Most agents have a single-file default (`stewardship.md`,
  `accuracy.md`, `rigor.md`, `craft.md`, `voice.md`); **Sentinel's
  standards source of truth is the shared `MASTER_PLAN.md` +
  `DEVELOPMENT_PLAYBOOK.md`** — no derived role-file (she watches over
  those docs and holds herself to them as much as she audits others
  against them). Framework templates §8.1 + deployment layout §8.2
  updated: Sentinel ships no `vigilance.md.template`; a new
  `framework-vault/` directory in the deployment holds her standards
  source (MASTER_PLAN.md + DEVELOPMENT_PLAYBOOK.md, deployment-
  specific copies). New audit rule `profile-standards-source-not-
  found` catches dangling references.

- **0.1.0-spec.4 (2026-05-23 PM)** — two-doc identity model per agent.
  New §2.5 "Identity + Standards" formalizes the SOUL.md (who I am)
  + core standards doc (the quality floor I refuse to fall below)
  pairing. Both docs are always-injected at skill-load time; they
  answer different questions and revise at different cadences. Per-
  role core docs named:
  - CoS → `stewardship.md`
  - KB → `accuracy.md` (per AJ)
  - Sentinel → `vigilance.md`
  - Analyst → `rigor.md`
  - BD → `craft.md`
  - Writing → `voice.md`

  Framework templates ship both files per role (deployments
  customize/expand/delete freely; audit warns on missing standards,
  blocks on missing SOUL). Framework structure §8.1 and deployment
  layout §8.2 updated to show both files. `deployment.yaml` schema
  §9 now carries `persona_file` + `standards_file` per profile.
  FinanceAgent example in the manifest extended to show how a
  custom role wires its own quality floor.

- **0.1.0-spec.3 (2026-05-23 PM)** — vendor-neutrality pass.
  HermesAgency is inference-agnostic; the framework names no specific
  vendor. New §1.3 "Vendor-neutral by design" codifies the
  commitment + introduces a new audit rule (`framework-vendor-leak`)
  that flags any framework-level file containing a vendor name.
  Deployment.yaml example in §9 generalized — no specific provider
  values, just placeholders that the deployment fills in.
  `nomic-embed-text` reference in the learning schema replaced with
  "deployment picks the embedding model." Appendix A item 8 BYO-
  inference rewritten as a first-class architectural commitment.
  All Claude/Anthropic/DeepSeek/Opus specific references removed
  from the spec (they may appear in vendor-enumeration docs as
  EXAMPLES of compatible providers; they no longer appear as defaults
  or as architectural primitives).

---

### Release-level revisions

- **v0.1.0 (2026-05-23)** — First shippable release. Six-week build
  delivered: framework skeleton, learning subsystem (the spine),
  autonomy + verifier + graduation gate + send-guard, Sentinel +
  events.db + 7-category audit, six role templates + scaffolds +
  reference deployment, `agency init` wizard + CLI + control panel +
  public docs. Pushed to `github.com/ajcrabill/hermes-agency` MIT.
  Test suite: 92 tests across seams + audit + e2e.

- **v0.2.0 (2026-05-23 PM)** — Hermes integration + agency-vault +
  Tier 3 interview. `_framework/hermes_patches/` carries the actual
  injection patches against the Hermes engine. `_framework/kanban/`
  + `_framework/cron/` shims bridge to Hermes' scheduler with a
  HermesAgency-owned `tracks` link type. Heartbeats write path lands
  for `operational-state.md` + `conversation-journal.md`.
  `templates/agency-vault/` ships Goals/Values/Personal/Work/Clients
  doc templates. New Tier 3 interview generates first drafts of
  agency-level docs from a deep conversation with the operator.
  Google Drive OAuth integration for CoS via `_framework/integrations/
  google_drive.py`. `standards.md.template` refactored to v7 richer
  structure. One real reference SKILL.md per role.

- **v0.3.0 (2026-05-23 PM)** — Coverage release. 35 starter skills
  filled in across all six roles. New `_framework/crm/` module:
  contacts, leads, sent_threads, four-priority reply matcher
  (thread_id → email → domain → unmatched). New
  `_framework/per_subject_state/` for per-author / per-coach /
  per-prospect scratchpads with filesystem namespace guard.
  Google Calendar integration stub + setup. Script template library
  (pipeline-watchdog, triage-batch, archive-enforcer, etc.) lands
  under `templates/scripts/`.

- **v0.4.0 (2026-05-23 PM)** — Agent personalization + manuscript
  coaching centerpiece. Tier 3 wizard extended with per-agent
  personalization (name override, pronouns, personality stub).
  Coaching subsystem (`_framework/coaching/`) lands as the missing
  manuscript-creation centerpiece: users / projects / phases /
  qa_history / deliverables / ingested_files. The no_agent cron
  pattern documented in §5.6 of the playbook — deterministic scripts
  that call inference as a tool, NOT LLM agents with DB write
  authority (key v7 lesson). Under-covered v7 skills back-filled:
  push-notify, obligation-board (later refactored), hardware-sourcing
  (later generalized).

- **v0.5.0 (2026-05-23 PM)** — Prototyping flywheel + obligation /
  shopping cleanup. `obligation-board` skill refactored to
  `obligation-extractor` + a `obligation` kanban tenant — kanban is
  the single source of truth for actionables, the skill just
  extracts them. `hardware-research` generalized to
  `shopping-research` (asks user for spec details + min/max price,
  then scours world). New `_framework/prototyping/` module:
  `ingest.py` (any source → corpus), `style.py` (derive formatting +
  voice from examples), `iteration.py` (stuck-loop diagnostic). New
  shared skills `prototype-from-example` + `iteration-tracker` under
  `_framework/skills/` are role-neutral. All Writing + draft skills
  updated to use the prototyping flywheel.

- **v0.6.0 (2026-05-23 PM)** — CoS time-use analyzer + SMART goal
  coach + Goals.md round-trip. `_framework/goals/`: `goals_md.py`
  (markdown ↔ structured store round-trip), `smart.py` (SMART
  criteria validator), `tracking.py` (goal_metrics +
  goal_observations + goal_milestones; linear-pace status:
  on-track / at-risk / missed / done / no-data). Two CoS skills:
  `time-use-analyzer` (calendar vs Goals.md drift report) and
  `smart-goal-coach` (Q&A coaching that drafts SMART goals into
  Goals.md). Closes the accountability loop: written goals → tracked
  metrics → weekly progress verdict.

- **v0.7.0 (2026-05-23 PM)** — Gmail API integration + T2 wizard +
  v7 migration tool. `_framework/integrations/gmail.py` lazy-imports
  the Google client; profile-local credentials. Tier 2 wizard's
  interactive flow now wires the OAuth handshake end-to-end. New
  `_framework/migration/v7_learning.py`: reads v7 learning corpus,
  plans the diff, applies idempotently with a journal so the
  operator can dry-run + replay. Live-verified against AJ's 304-rule
  v7 corpus (270 ready to migrate on first run; 34 deferred for
  manual review due to schema-shift).

- **v0.8.0 (2026-05-23 PM)** — FinanceAgent role + finance
  subsystem. Seventh role lands (`templates/profiles/finance/`)
  with its own SOUL.md + `standards.md` + 7 reference skills:
  cash-flow-tracker, burn-rate-monitor, invoice-management,
  revenue-attribution, expense-categorizer, budget-vs-actual,
  quarterly-financial-summary. New `_framework/finance/`:
  `finance_db.py` (invoices_in / invoices_out / expenses / revenue /
  vendor_payments / budget_lines tables) + `computations.py`
  (cents-as-integers; no floating-point for cumulative money).
  `_framework/invariants.yaml::roles` extended with the
  finance role keyword block.

- **v0.9.0 (2026-05-23 PM)** — Goal tracking + weekly brainstorm +
  cleanup. Long-deprecated `obligationboard` (pre-v7) finally
  removed from references; replaced by kanban. OpenWebUI references
  pulled from invariants — operator's choice whether to integrate,
  framework doesn't ship it. Multi-machine + other agents deferred.
  New CoS skill `weekly-brainstorm` — surfaces three actionable
  ideas per week for how HermesAgency could autonomously move the
  needle on Goals.md. New CoS skill `goal-progress-tracker` —
  weekly verdict per goal (on-track/at-risk/missed) with the
  underlying metric data.

- **v0.10.0 (2026-05-24)** — Two-tier quality auditor + cost
  attribution + markdown projector + OTP auth + auto-reapply
  patches. `_framework/quality/`: continuous scoring per skill;
  overall = min(dimensions) ("chain as strong as weakest link");
  trusted ≥ 0.80 / watching 0.65–0.80 / undelegated < 0.65, with
  auto-undelegation when watching breaches threshold.
  `_framework/cost/`: operator-registered pricers (vendor-neutral —
  wildcard fallback if no specific pricer matches);
  cost-per-skill / cost-per-correction visibility.
  `_framework/state/markdown_projector.py`: 4 built-in projectors
  (learning, goals, finance, prototypes) regenerate human-readable
  markdown views from canonical DB state. `_framework/ops/auth.py`:
  email-OTP auth on the control panel (6-digit hashed, 10m expiry,
  5-attempt lockout, 24h sessions). `_framework/hermes_patches/
  auto_reapply.py`: fingerprint detection so HermesAgency's patches
  re-apply themselves after a Hermes upgrade overwrites them.
  v0.10.1 patched a `framework-vendor-leak` (openai-compat example
  in pricing.py docstring) to keep the audit clean.

- **v0.11.0 (2026-05-24)** — Signal + Slack ingress + PyPI prep.
  `_framework/integrations/signal.py` bridges signal-cli via
  subprocess + JSON-RPC mode (operator runs `signal-cli register`
  separately; framework doesn't bundle it).
  `_framework/integrations/slack.py` calls the Slack web API via
  urllib (no `slack_sdk` dep). CoS `owner-channels-ingress` skill
  updated to poll all four channels (email/Signal/Slack/dashboard
  chat tab) alongside email. PyPI publishing prep complete:
  `pyproject.toml` Beta classifier + optional-deps split
  (google / voice / ingest / embed / dev with build + twine).
  `MANIFEST.in` includes README/CHANGELOG/CONTRIBUTING +
  `recursive-include templates` + `_framework` YAML + docs.
  `CONTRIBUTING.md` lands. Test suite: 198 tests across all seams,
  audit clean.

- **v0.11-spec.0 (2026-05-24)** — Spec moves into the repo at
  `docs/HERMES_AGENCY_SPEC.md` (was: v7 vault). All eleven
  release-level revisions captured above. Spec is now the living
  source of truth for design; CHANGELOG.md remains the
  user-facing release log. Title rolled from "v0.1 Specification"
  to "Specification" — the spec is no longer a one-version
  artifact.

- **v0.12.0 (2026-05-24)** — Spec-into-repo + five new
  opportunity-hunting skills. KB `weekly-industry-newsletter`,
  Writing `thought-leadership-scanner` (niche-first, highly
  curated), BD `existing-client-commonality-analyzer`, BD
  `referral-opportunity-scanner`, BD `potential-clients-pipeline`.
  Tests: 198 passing. Audit clean. v0.12.1 + v0.12.2 are UX-fix
  patches from AJ's first real install — added `agency next`
  command, T2 wizard resume-hints, framework_version stale-
  hardcode fix, raw-secret rejection in credential prompt,
  `--tail N` ergonomics, case-consistency check in profile-id
  prompts.

- **v0.13.0 (2026-05-24)** — Hermes-as-first-class-prerequisite.
  The wizard's first step is now Branch A (detect existing
  Hermes) or Branch B (install Hermes for the user). The
  framework refuses to pretend it's a valid deployment when no
  engine is present. New `_framework/hermes_engine/` subsystem
  (detection + installer). New `agency init --hermes-only` for
  out-of-order recovery. `agency status` surfaces Hermes
  detection front-and-center; `agency next` treats Hermes-missing
  as BLOCKER #1; `agency hermes-patches apply` and `agency cron
  sync` hard-error if Hermes isn't detected. Schema: new
  `deployment.yaml::engine` block. v0.13.1 adds `bootstrap.sh`
  one-command installer + `agency reset` command for clean
  re-init + install.sh framework_version hardcode fix. v0.13.2
  flipped repo to public (MIT) and re-front-loaded docs around
  the curl-pipe one-liner.

- **v0.14.0 (2026-05-24)** — `agency chat` added. The framework
  gained its first built-in inference path: `_framework/runtime/`
  with provider config resolver, prompt composer (SOUL +
  standards + applicable learning rules + session framing), and
  stdlib-only HTTP client. *Retrospectively, this was a wrong
  turn* — see v0.15.0 below. v0.14.0 was added to answer "how do
  I use this thing right now," but the correct answer was always
  "via `hermes chat` with patches applied." `agency chat` should
  have been a diagnostic from the start. v0.15.0 demotes it.

- **v0.15.0 (2026-05-24)** — **Architectural reset: plugin
  framing restored.** AJ pointed out the framework had drifted
  from "Hermes plugin" toward "parallel framework." The spec's
  first sentence (*layered on Hermes*) was correct intent, but
  v0.3 → v0.14 added parallel surfaces (own state, own chat,
  own panel, own runtime). v0.15.0 corrects the *narrative* +
  exposes the honest integration state:

    - New §1.4 "Plugin discipline" — constitutional rule: every
      reliability system must be a Hermes hook. No parallel
      runtimes. No daily-use commands that compete with `hermes
      chat`.
    - New §1.5 — the explicit 7-system table with each
      system's Hermes-hook shape.
    - New §13.6 — closure roadmap for v0.16 → v0.19 to build
      the missing patches (autonomy gate, verifier, send-guard)
      and collapse parallel state.
    - New `agency hermes-patches systems` command — the honest
      integration inventory. Reports 4/7 wired into Hermes
      today (learning loop, Sentinel, kanban-tracks, audit) +
      3/7 still parallel with explicit "PATCH NOT YET BUILT"
      markers. `_framework/hermes_patches/apply.py` carries
      `SYSTEM_INVENTORY` as the source of truth for what the
      framework claims and what's actually wired.
    - `agency chat` demoted to **diagnostic surface**. Prints a
      banner on every invocation pointing users to `hermes chat`.
      `--no-banner` for scripted use. README + bootstrap.sh
      post-install message + CLI help all redirect daily use to
      `hermes chat`.
    - `agency panel` demoted in docs (read-only diagnostic UI,
      not a primary surface).
    - README tagline: "A Hermes plugin that adds 7 reliability
      systems for small-agency owners..." (was: "A multi-agent
      framework..."). "How you use it" leads with `hermes chat`
      after `agency hermes-patches apply`.
    - bootstrap.sh "Done" footer points users at the canonical
      sequence: `agency hermes-patches apply` → `agency hermes-
      patches systems` → `hermes chat`.

  No new features ship in v0.15.0. The work is narrative +
  surface-correction. The actual integration gap (3 missing
  patches + parallel state) is closed across v0.16–v0.19.

- **v0.16.0 (2026-05-24)** — The 4-step install. bootstrap.sh drops
  Hermes-install Branch B (per plugin discipline: framework doesn't
  install runtime). `agency migrate v7 --from <dir>` accepts a v7
  home directory and does full migration in one command (learning
  corpus + SOULs + standards + vault MDs + legacy DBs). Wizard's
  Hermes-install path removed. README leads with the literal 4-command
  install recipe.

- **v0.17.0 (2026-05-24)** — **Architectural pivot to Hermes plugin
  API.** While preparing the missing-patch work for v0.17 (autonomy
  gate, verifier, send-guard), discovered that Hermes has a documented
  plugin API exposing exactly the lifecycle hooks we need:
  `pre_llm_call`, `pre_tool_call`, `post_tool_call`, `on_session_start`,
  `on_session_end`. PluginManager auto-discovers plugins from
  `~/.hermes/plugins/<name>/`. Plugins register hooks + slash commands
  via `register(ctx)`.

  This release pivots HermesAgency from "framework that text-patches
  Hermes' source" to "Hermes plugin that registers hooks via the API."
  Same outcome (all 7 reliability systems wired into Hermes execution),
  better implementation (no source-tree fragility, Hermes maintains the
  hook contract). The four previously-parallel systems (learning loop,
  autonomy ladder, verifier, send-guard) all become plugin hooks in one
  release — no longer a v0.17/v0.18/v0.19 staged plan.

  New: `hermes_agency_plugin/` package at the repo root with
  `plugin.yaml` + `__init__.py::register(ctx)` + hook handlers + slash
  command handler. bootstrap.sh symlinks `~/.hermes/plugins/hermes-agency
  /` → the plugin package; Hermes discovers on next launch.

  Deprecated: `_framework/hermes_patches/` (text-anchor patches).
  REGISTRY now empty by design; module kept as no-op for one release,
  removed in v0.18.

  All 7 reliability systems report wired via `agency hermes-patches
  systems`:
  - Learning loop (pre_llm_call)
  - Autonomy ladder (pre_tool_call)
  - Verifier (post_tool_call — observation only in v0.17, enforcement
    in v0.18)
  - System Sentinel (on_session_start / on_session_end)
  - Kanban tracks-link (shim, unchanged)
  - Send-guard (pre_tool_call filtered to mail tools)
  - Audit (script, unchanged)

  `/agency` is now a Hermes slash command — supervisory surface lives
  inside `hermes chat`. Subcommands: status, next, systems, capture,
  learn list, audit, setup (stub for v0.19).

  Tests: 224 passing + 4 skipped (deprecated text-patch tests, to be
  deleted in v0.18). Audit clean.

  Closure plan now narrower and faster: v0.18 = verifier enforcement
  + deprecated-module removal; v0.19 = `/agency setup` migration-or-
  clean-install in-Hermes interview; v0.20 = parallel-state collapse.

- **v0.17.1-spec (2026-05-24)** — *Spec-revision pass; no code change.*
  AJ asked: "if you were designing HermesAgency from scratch knowing
  what we know now about Hermes' plugin API, what would it look like?"
  This revision rewrites the spec to reflect that from-scratch design
  and treats v0.18–v0.22 as the cleanup path from current state to the
  ideal.

  Specifically:
  - **Tagline (§1)** — "*continuously-learning, multi-agent plugin for
    Hermes Agent, built for small-business owners*" (was: "multi-agent
    framework for small-agency owners"). Sharper plugin framing; small-
    business broadens beyond small-agency; "continuously-learning"
    captures the supervised-correction loop without invoking the
    technical ML term "deep learning."
  - **§0 Document purpose** — adds an explicit architectural arc
    summarizing v0.1 → v0.22 so a new reader understands where the
    project came from and where it's going.
  - **New §2.0 "Plugin shape"** — establishes plugin-from-the-start as
    the foundation everything else rests on. Five direct consequences
    spelled out (Hermes is the runtime, state next to Hermes', profiles
    are Hermes agents, skills are agentskills.io-compatible, no agency
    init wizard).
  - **§8.1 Repo layout rewritten** — shows the target v0.20+ layout
    (`hermes_agency_plugin/` is the whole codebase; `_framework/`
    retired) and notes the current v0.17 mid-transition shape.
  - **§8.2 Deployment layout rewritten** — adds the target post-v0.20
    layout where all state lives at `~/.hermes/agency-state/` (no
    separate `~/.agency/` world).
  - **§8.4 Two-tier file ownership rule** updated for plugin shape
    (header changes "FRAMEWORK" → "PLUGIN"; deployment-edited content
    lives in `~/.hermes/agency-state/vaults/<id>/`).
  - **§11 Operator surface rewritten** — `/agency` slash command (in-
    Hermes) is the primary surface; standalone shell `agency` command
    is a thin shim for non-interactive contexts only; control panel
    is read-only diagnostic.
  - **§13.7 Closure plan rewritten** — replaces the v0.16–v0.19 patch
    plan (which v0.17 made obsolete by pivoting to the plugin API)
    with the v0.18–v0.22 structural cleanup: verifier enforcement,
    `/agency setup` interactive interview, structural rename + state
    collapse, agentskills.io conformance, PyPI publication. Each
    release acceptance-tested.
  - **Spec version** rolled to v0.17.1.

  No code changes in this revision — it's documentation alignment.
  Codebase work continues on the v0.18–v0.22 plan above.

- **v0.17.2-spec (2026-05-24)** — *Spec-revision pass; no code change.*
  Added §0.5 Lineage section + Good Ancestor attribution in spec
  header. Dual-version notation introduced (public release version
  + "v0.M of the Nth effort" internal counter).

- **v0.18.0 (2026-05-24)** — Verifier enforcement + deprecated-
  patches removal. Plugin's `transform_tool_result` hook runs ad-hoc
  verifier criteria against tool outputs (file_exists / file_contains
  for write_file / patch / edit_file); failures get rewritten as
  actionable LLM errors. `_framework/hermes_patches/` deleted; tests
  cut; `SYSTEM_INVENTORY` moved to `hermes_agency_plugin/
  system_inventory.py`. Net -364 lines. 226 passing, zero skipped.

- **v0.19.1-spec (2026-05-24)** — *Positioning revision; no code change.*
  AJ wrote out the polished pitch paragraph — the prose version of
  the three-pillar tagline. Threaded through the spec, README, and
  package descriptions.

  Key new framing elements:
  - "Multi-agent framework built as a plugin to NousResearch's
    powerful Hermes agentic engine" — calls Hermes by its full
    descriptive name ("agentic engine") rather than just "engine"
  - "Designed *for* and *by* small-business owners" — emphasizes
    AJ as the principal user, not just the developer
  - "Pulls together the suite of capabilities every small business
    wants and needs but typically can't afford" — names the gap
  - **The collaboration model:** "where the powerful, always-working
    aspects of *technological intelligences* (the agents) collaborate
    with the ingenuity and creativity of *biological intelligences*
    (the humans)" — the philosophical core; agents contribute
    consistency, persistence, parallel attention, tireless follow-
    through; humans contribute judgment, taste, originality, ethical
    anchoring, moments of insight
  - "7-part continuous learning framework designed from the ground
    up to rapidly expand the agents' understanding of the human's
    goals and values" — names the seven systems with a coherent
    purpose ("expand understanding of goals + values")
  - "Advantages of companies many times their size and revenue" —
    sharper competitive framing than "small-business at a
    disadvantage"

  Updated surfaces:
  - **Spec §1 (The promise)** rewritten around the new framing.
    Adds an explicit "collaboration model" subsection naming what
    each kind of intelligence contributes.
  - **README** lead paragraph replaced with the polished pitch
    immediately under the three-pillar tagline + badges.
  - **pyproject.toml** description picks up "many times your size"
    + "without surrendering ownership" as the punchiest summary.
  - **plugin.yaml** description echoes the "technological /
    biological intelligences collaborate via 7-part continuous
    learning framework" framing for plugin-listing pages.

  Spec version → v0.19.1-spec. plugin.yaml → 0.19.1 (description-
  only change; code path unchanged from v0.19.0). No code, no test
  delta.

- **v0.18.2-spec (2026-05-24)** — *Spec-revision pass; no code change.*
  Added the three-pillar tagline and the big-tech-contrast section.
  Spec sections §1.5 (three pillars), §1.6 (why-this-matters-now /
  big-tech contrast), §1.7 (seven reliability systems — renumbered
  from previous §1.5) restructure the "what is this and why now"
  framing:

  - **§1.5 The three pillars**: Powerful Autonomous Team / Continuous
    Context Learning / Complete Privacy & Data Control. Each pillar
    grounded in the architectural commitment that makes it real.
  - **§1.6 Why this matters now**: every large platform is rolling
    out the same features (AI assistants, multi-agent workflows,
    persistent memory, learning from corrections) — a small business
    without these is at a real disadvantage; but the big-platform
    versions come at a price (ecosystem lock-in, data exfiltration,
    per-seat economics). HermesAgency gives small-business owners the
    same capabilities without trading the data, IP, or ideas that make
    their business distinct. Four architectural commitments enumerated:
    runs on your hardware, vendor-neutral inference, MIT/open-source/
    no-telemetry, your IP stays yours.
  - **§1.7 Seven reliability systems**: unchanged content, renumbered
    from §1.5.

  README header: lead with "Powerful Autonomous Team. Continuous Context
  Learning. Complete Privacy & Data Control." subtitle + a "Why this
  exists" section that's the big-tech contrast condensed for the
  front page.

  pyproject.toml description updated to lead with the three pillars.

  Spec version rolled to v0.18.2.

- **v0.18.1-spec (2026-05-24)** — *Spec-revision pass; no code change.*
  Fleshed out §0.5 Lineage with the real 9-version history AJ
  provided. Each version now carries hardware / model / runtime
  context and the architectural lesson that triggered the next
  rewrite:

  - v1: VPS + OpenClaw + Sonnet
  - v2: esb-m1 (64 GB) + Claude Cowork + Opus
  - v3: complete rewrite, same stack
  - v4: dCoS (first SQLite-backed state model)
  - v5: dCoS rebased onto Hermes Agent
  - v6: Hermes update + DeepSeek (vendor-neutrality crystallized)
  - v7: Hermes profiles + kanban (the multi-agent reframe)
  - v8: HermesAgency standalone soft-fork on esb-m4 (128 GB) +
       DeepSeek + local inference (Qwen 3.6, Gemma 4)
  - v9: HermesAgency as proper Hermes plugin (the v0.17 pivot)

  Added a "Pattern across the 9 versions" subsection naming the
  three forces that drove each rewrite: hardware ceilings, runtime
  contract changes, and architectural mistakes taught. The current
  shape (Hermes plugin with seven hooks) is the answer that
  survives all three forces. Architectural arc summary in §0 also
  updated to reference the 9-version lineage. Spec version rolled
  to v0.18.1.
