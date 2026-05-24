# HermesAgency — Specification

**Version:** v0.15.0 (2026-05-24)
**Status:** Living spec — tracks shipped releases
**Author:** Drafted with AJ
**Home:** `github.com/ajcrabill/hermes-agency` (MIT)

---

## 0. Document purpose

This is the build + design specification for **HermesAgency** — a
Hermes plugin that adds 7 reliability systems on top of NousResearch's
Hermes engine, designed for small-agency owners and operators.

The spec was written *before* code so the architecture could be reviewed,
revised, and locked before any building. AJ is the first customer; his
v7 system is migrating to HermesAgency via the v7-migration tool
(`agency migrate v7`).

This document is the source of truth for the framework's design.
Sections §0–§15 describe the architecture and roadmap as locked at
v0.1; §16 (change log) tracks every formal revision since, including
all release-level versions. New features land through the release
cycle and accrete in the change log; sections above are revised
when the underlying architecture changes.

**Architectural reset at v0.15 (2026-05-24):** Through v0.1–v0.14, the
implementation drifted from "Hermes plugin" toward "parallel framework
with its own state, chat, panel, and runtime." The spec's first
sentence — *layered on Hermes* — was the design intent throughout,
but most subsystems got built as `_framework/<x>/` modules with their
own state under `~/.agency/_state/<x>.db`, called by the agency's own
code paths rather than by Hermes during skill execution. v0.15.0
corrects the *narrative* (new §1.4 "Plugin discipline" + the
`agency hermes-patches systems` honesty-surface). v0.16–v0.19
correct the *implementation* by building the missing patches and
collapsing parallel state. See §13 for the closure roadmap.

---

## 1. The promise — what this framework is for

**HermesAgency is a multi-agent framework for small-agency owners who
refuse to re-teach their AI ten times.**

Every correction the owner gives is captured, tagged, propagated to every
relevant agent across the agency, and applied without the owner repeating
themselves. The autonomy ladder lets agents earn more independence over
time — but only when the learning loop is provably working. The system
tells the owner when it isn't.

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
reliability system it adds (the 7 in §1.5) must be expressed as a
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

v0.15.0 adds **`agency hermes-patches systems`** as the honesty
surface. It prints the 7 systems and which are actually Hermes-
extending today. Any "PATCH NOT YET BUILT — system is parallel,
not Hermes-extending" line in that output is an architectural
debt that v0.16+ closes. The audit (§14, future rule
`framework-parallel-state-leak`) will eventually enforce this at
commit-time, refusing changes that add new `_framework/<x>/`
state-owning subsystems without a corresponding hook.

The discipline:

- **New reliability systems** must propose their Hermes-hook
  shape (patch into a Hermes file, or shim over a Hermes table)
  before any standalone code is written.
- **Existing parallel modules** (autonomy, verifier, send-guard,
  any of the v0.3+ subsystems that ended up parallel) are
  architectural debt to be repaid via the v0.16–v0.19 plan.
- **`agency hermes-patches systems`** is the public source of
  truth for whether the discipline is being kept.

### 1.5 The seven reliability systems

The exhaustive list of what HermesAgency adds to Hermes:

| # | System | Hook into Hermes |
|---|---|---|
| 1 | Supervised learning loop | Patch into `_build_skill_message` / `skill_view` to inject applicable rules at skill-load |
| 2 | Autonomy ladder (L1–L5) | Pre-action gate patch in Hermes' skill executor (consults `_framework.autonomy`) |
| 3 | Verifier (per-skill criteria) | Post-completion hook in Hermes' skill-exit path (runs the skill's frontmatter verifier block) |
| 4 | System Sentinel (read-only) | Reads Hermes' `state.db` event log via shim; emits to agency events log |
| 5 | Kanban tracks-link type | Shim writes `tracks` rows into Hermes' own `kanban.db` |
| 6 | Send-guard (outbound mail gate) | Pre-send hook on Hermes' email-send path (consults `_framework.send_guard`) |
| 7 | Audit (weekly alignment) | Scheduled script reading Hermes state + agency state; produces findings, not actions |

Systems 1, 4, 5, 7 are Hermes-native in v0.15.0. Systems 2, 3, 6
are parallel debt; their patches are the v0.16–v0.18 closure plan.

---

## 2. Architecture overview

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

### 8.1 Repo layout (the public framework)

```
hermes-agency/                          (github, MIT)
├── README.md                           (public-facing pitch + quickstart)
├── LICENSE                             (MIT)
├── DEVELOPMENT_PLAYBOOK.md             (the playbook, generic v2.0.0)
├── HERMES_AGENCY_SPEC.md               (this document, post-build)
├── CHANGELOG.md
├── docs/
│   ├── ARCHITECTURE.md                 (the diagram in §2.2)
│   ├── ROLES.md                        (the 6 roles in §7)
│   ├── DEPLOYMENT.md                   (how to install + agency init)
│   ├── LEARNING_LOOP.md                (§1.1 + §3, the central promise)
│   ├── AUTONOMY.md                     (§4 ladder)
│   ├── SENTINEL.md                     (§5)
│   ├── PATCHES_TO_HERMES.md            (the reapply hook list)
│   └── examples/
│       └── minimal-deployment/         (smoke-test reference deployment)
├── _framework/
│   ├── constants.py                    (path constants, brand-agnostic)
│   ├── invariants.yaml                 (ALWAYS_BLOCK, tenants, action classes, providers)
│   ├── manifest.py                     (deployment.yaml schema + validator)
│   ├── learning/                       (§3 — the spine)
│   │   ├── learning_db.py
│   │   ├── rule_injection.py
│   │   ├── firings.py
│   │   ├── recapture_detector.py
│   │   ├── tag_resolver.py
│   │   ├── correction_capture.py
│   │   └── compliance_report.py
│   ├── autonomy/                       (§4)
│   │   ├── autonomy_db.py
│   │   ├── autonomy_gate.sh
│   │   ├── autonomy_engine.py
│   │   └── graduation_audit_gate.py
│   ├── verifier/                       (§6.1)
│   │   ├── verifier.py
│   │   └── criterion_types/
│   ├── sentinel/                       (§5 — Sentinel is framework code, not deployment)
│   │   ├── events_db.py
│   │   ├── learning_monitor.py
│   │   ├── drift_monitor.py
│   │   ├── heartbeat_watch.py
│   │   └── event_rollup.py
│   ├── kanban_patches/                 (§6.3 — two link types)
│   ├── send_guard/                     (§6.4)
│   ├── scaffolds/                      (scaffold-skill / scaffold-script / scaffold-profile / scaffold-deployment)
│   ├── audit/                          (audit-alignment.py + per-rule history)
│   ├── lifecycle/                      (T1/T2/T3 flow + flip-live.py)
│   └── skills/                         (cross-agent shared skills — development-playbook, prompt-injection-defense)
├── templates/
│   ├── deployment.yaml.template
│   ├── persona.md.template             (SOUL.md with placeholders)
│   └── profiles/                       (per-role profile templates — each ships TWO identity docs per §2.5)
│       ├── chief-of-staff/             (SOUL.md.template + standards.md.template + skills/)
│       ├── knowledge-base/             (SOUL.md.template + standards.md.template + skills/)
│       ├── system-sentinel/            (SOUL.md.template + standards.md.template + skills/) — Sentinel's standards.md references master plan + playbook
│       ├── analyst-judge/              (SOUL.md.template + standards.md.template + skills/)
│       ├── business-development/       (SOUL.md.template + standards.md.template + skills/)
│       └── writing-support/            (SOUL.md.template + standards.md.template + skills/)
├── install.sh                          (the `agency init` wizard)
└── tests/
    ├── seams/                          (system seam tests)
    ├── audit/                          (audit-rule tests)
    └── e2e/                            (end-to-end smoke tests)
```

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
├── _state/                             (shared, cross-profile)
│   ├── kanban.db
│   ├── learning.db
│   ├── autonomy.db
│   ├── events.db
│   ├── heartbeats.db
│   └── drift_scores.json
└── _health/
    ├── audits/                         (audit reports + scoreboard)
    ├── operator-actions.jsonl
    └── recapture-history.jsonl
```

### 8.3 Brand-agnostic paths

Every path that exists in a v7-style deployment as `~/.<owner>/...` becomes `~/.agency/...` under HermesAgency.
The owner's chosen agent names (e.g., "Loriah" for CoS, "Lynda" for
Analyst) live ONLY in the identities/ persona files and in `profile.id`
in deployment.yaml — never in paths, never in plist labels, never in
env var names.

Plist labels: `com.hermes-agency.cron.<profile-id>.plist`. The `profile-id`
is the deployment's chosen name; the rest is framework-fixed.

### 8.4 Two-tier file ownership rule

Every file in `_framework/` carries a header:
```python
# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment;
# customizations belong in ~/.agency/profiles/<P>/ or deployment.yaml.
```

Every file in a deployment's `profiles/` carries:
```python
# OWNER — deployment-specific. Framework upgrades will not touch this.
```

The audit (§10) checks that framework files don't contain literal owner
names, mail addresses, or contact references — pure framework code,
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

### 11.3 CLI

```
agency status              # quick health summary
agency init                # the wizard
agency upgrade             # framework version bump
agency audit               # run audit-alignment.py
agency capture "..."       # interactive correction capture
agency promote <skill>     # force-promote (with audit gate)
agency demote <skill>      # force-demote
agency events --tail       # live events feed
agency learn list          # list learning rules
agency learn show <id>     # show rule + firings
```

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

- Final delta sync (any v7 state not yet in .agency)
- AJ flips authoritative bit
- v7 archived (frozen, read-only) for 6 months as a fallback
- After 6 months stable on .agency, v7 deleted

### 13.6 Plugin-integration closure plan (v0.16 → v0.19)

After v0.15.0 corrected the narrative (the framework is a Hermes
plugin, not a parallel runtime), three patches and one cleanup
release close the implementation gap. Each is a release-sized
chunk of real engineering.

**v0.16.0 — `autonomy-gate` patch**

Patch into Hermes' skill executor (the function that decides
whether to execute a proposed action vs. require operator
approval). Before any L2+ action fires, the patch consults
`_framework.autonomy.allowed(skill_id, profile, action_class)`.
Refused actions become drafts in the kanban with the autonomy
verdict attached. The autonomy ladder (§4) becomes load-bearing
instead of advisory.

Acceptance: a skill at L1 (`draft-only`) that tries to emit a
`structural-change` action gets caught by Hermes itself, not by
agency-side bookkeeping. `agency hermes-patches systems` reports
"Autonomy ladder (L1–L5)" as wired.

**v0.17.0 — `post-completion-verifier` patch**

Patch into Hermes' skill-exit hook. After a skill completes, the
patch runs the skill's `verifier:` block from its frontmatter
(§6.1) against the output. Failures cause Hermes to refuse the
skill's completion (back to draft state) until the verifier
passes. The verifier registry from `_framework.verifier`
gets wired in as the gate.

Acceptance: a skill whose verifier asserts `file_contains` on a
generated draft fails immediately if the draft is missing the
required content. The skill doesn't claim "done" until the
verifier passes. `agency hermes-patches systems` reports
"Verifier (per-skill criteria)" as wired.

**v0.18.0 — `outbound-mail-guard` patch**

Patch into Hermes' email-send path (whatever Hermes uses to
hand off to the configured mailer). Before any outbound message
leaves, the patch consults `_framework.send_guard.check(...)`.
The send-guard's first-message hard-rules + per-recipient
cooling periods become load-bearing instead of advisory.

Acceptance: an attempted outbound mail to a recipient who's
under a "first-touch hard rule wait" gets refused at Hermes'
send path. The kanban gets a card explaining the refusal.
`agency hermes-patches systems` reports "Send-guard (outbound
mail gate)" as wired.

**v0.19.0 — Parallel-state collapse**

The remaining `_framework/<x>/_state/*.db` databases (learning,
events, autonomy, quality, cost, goals, finance, crm, coaching,
prototypes, per_subject_state) get migrated to sidecar tables
under `~/.hermes/agency-state/<x>.db` (the convention being:
"state HermesAgency owns, but stored next to Hermes' own DBs
so anything reading Hermes state can find it"). Read paths
update to look there first, fall back to `~/.agency/_state/`
during a one-release migration window, then become
authoritative.

Acceptance: a fresh Hermes install with HermesAgency layered
on top has a single `~/.hermes/` state directory. The agency
framework owns no separate state world. `agency status` reports
"state location" as `~/.hermes/agency-state/` with zero rows
in any `~/.agency/_state/` paths.

After v0.19.0, the framework is what the spec said it would be:
a Hermes plugin with seven Hermes-extending hooks, sharing
state with Hermes, never running as a parallel surface.

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
