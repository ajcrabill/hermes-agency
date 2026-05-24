# HermesAgency development playbook

Version: 2.0.0
Audience: Anyone building skills, scripts, or profiles inside a
HermesAgency deployment.

This playbook is the framework's standards floor. It does not depend
on any specific deployment — every artifact you build inside any
`~/.agency/` is held to it. The audit (`agency audit`) checks against
the rules here; the graduation gate refuses promotion when ALWAYS_BLOCK
findings remain.

When the playbook and a deployment-specific convention conflict, the
playbook wins. When you need an exception, capture it as a learning
rule and propose a playbook revision via PR — don't fork the
discipline.

---

## 0. When this fires

You read this playbook (or have the audit read it for you) any time you:

- Create a new skill, script, or profile
- Promote a skill to a higher autonomy level
- Investigate why something failed
- Wonder whether what you're about to do is the framework's
  preferred shape

If you find yourself asking "is there a standard for this?" the
answer is probably here.

---

## 1. The five system seams

Everything in HermesAgency composes around five seams. When you
build, your artifact will touch one or more of them.

1. **Learning** — the spine. Owner corrections capture, propagate,
   inject, fire, and detect recapture. See `docs/LEARNING_LOOP.md`
   for the architecture; this playbook covers compliance.

2. **Autonomy** — the L1-L5 ladder. Every skill has a current level
   per-deployment; every consequential action runs through the
   autonomy gate first. Promotion needs three inputs: track record,
   structural compliance, learning fidelity.

3. **Verifier** — typed completion, fail-closed. Every kanban-
   completing skill declares a `## Verifier criteria` section.
   Zero criteria means completion is refused (fail-closed by design).

4. **Kanban** — the cross-profile work channel. One DB. Per-profile
   processor crons claim tasks where `assignee=<self>`. Two link
   types: `blocks` (gates completion) and `tracks` (aggregates).
   Avoid the umbrella-deadlock pattern by using `tracks` for parent
   tasks that aren't true dependencies.

5. **Send-guard** — outbound mail validation. Three layers: access
   list (white/grey/black) → hard ceilings → hard-rule validators.
   Hard-rule breaches record firings with `was_overridden=1` so the
   loop sees them.

If your skill or script reaches into multiple seams, plan how each
seam's contract holds. If you can't articulate it for a seam your
artifact touches, you haven't designed it yet.

---

## 2. Skill anatomy

Every skill is a directory: `profiles/<id>/skills/<name>/SKILL.md`.

Required structure (audit rule names in brackets):

- **Frontmatter with autonomy block**
  `[skill-no-autonomy-frontmatter]` — ALWAYS_BLOCK

  ```yaml
  ---
  skill_id: name
  profile: cos
  role: chief-of-staff
  autonomy:
    min_level: 1
    action_classes: [draft-only]
  voice_tags: [warm-not-flattering, we-not-i]
  ---
  ```

- **`## What this skill does`** — one-paragraph purpose.

- **`## Inputs`** — what the skill receives at invocation.

- **`## Supervised learning`**  `[skill-no-supervised-learning]` —
  ALWAYS_BLOCK. Must describe how the skill receives injected
  learning rules + records firings. Boilerplate the scaffold inserts
  is enough; just don't delete it.

- **`## Action surface`**  `[skill-no-action-surface]` — ALWAYS_BLOCK.
  Lists what the skill is permitted to do at its current level.

- **`## Verifier criteria`**  `[skill-no-verifier]` — ALWAYS_BLOCK.
  Declares typed criteria the verifier runs at completion. Empty
  block = fail-closed.

- **`## Failure modes`**  `[skill-no-failure-mode]` — warn. Document
  the known ways this skill fails. Each one should map to a
  verifier criterion.

- **`## Self-check`**  `[skill-no-self-check]` — warn. Questions the
  agent should ask itself before completing.

Optional but recommended:

- **`## Untrusted content`**  `[skill-no-untrusted-content]` —
  ALWAYS_BLOCK *for skills that handle external input* (email, RSS,
  scrape, webhook, ingest). The audit's heuristic flags external-
  facing skill names automatically.

- **`## Prompt-injection defense`** — when sandboxing external text,
  describe the strategy. **Paraphrase trigger phrases — never quote
  them verbatim.** Quoting them in the skill body is itself
  injection-vulnerable.  `[skill-injection-trigger]` — ALWAYS_BLOCK.

Use `agency scaffold-skill --name X --profile P --role R` to
generate a compliant skeleton. Audit passes on the generated file
by construction; if you find yourself fighting the audit, you've
diverged from the shape — fix the divergence.

---

## 3. Verifier criterion types

The verifier is the only thing that says "this task completed."
Skills declare typed criteria; the verifier runs each.

Ten registered types (v0.1):

| Type | What it checks |
|---|---|
| `file_exists` | Path exists |
| `file_contains` | File contains a needle |
| `file_not_contains` | File does NOT contain a needle |
| `sql_query` | Query rowcount matches expect_rows / min / max |
| `kanban_status` | Task is at the expected status |
| `kanban_descendants_done` | All `blocks`-children are done |
| `learning_rule_recorded` | A rule was captured matching source filter |
| `firing_recorded` | A firing was recorded for (rule, skill) |
| `http_status` | HTTP GET returns expected status |
| `shell_exit_zero` | Command exits 0 (use sparingly) |

Adding a type is a one-file PR. Prefer adding a typed checker to
re-using `shell_exit_zero` whenever the new criterion will be
re-used.

**Fail-closed rule:** zero criteria → completion refused. Always
declare at least one. If your skill genuinely produces nothing
verifiable (rare), declare `firing_recorded` for the learning
rule that the skill exists to apply.

---

## 4. Prompt-injection defense (the paraphrase-don't-quote rule)

If your skill processes external content (email, scraped web,
podcast transcript, ingested document, anything not authored by an
agent you trust), you must defend against prompt injection.

**Hard rule: when documenting the defense, paraphrase the trigger
phrase. Do not quote it verbatim.**

Why: the SKILL.md text itself gets injected into the model's context
on every skill load. If your skill body says
`watch for "IGNORE ALL PREVIOUS INSTRUCTIONS"`, you've embedded the
trigger phrase in the model's working context — the defense IS the
injection.

Right: "scanner watches for known authoritative-instruction trigger
phrases and short-circuits to defensive mode on match."

Wrong: any quoted, verbatim trigger phrase.

The audit's `skill-injection-trigger` rule catches the most common
ones; the principle generalizes to any phrase that could plausibly
hijack a model's instruction-following.

---

## 5. Script anatomy

Scripts live at `profiles/<id>/scripts/<name>.py`. Required:

- **Shebang line.** `#!/usr/bin/env python3` as line 1.
  `[script-no-shebang]` — ALWAYS_BLOCK.

- **Error handling.** Either `try/except` around the work, or an
  explicit `raise` in `if __name__`. Unhandled exceptions in cron
  jobs crash silently; the operator doesn't notice until something
  downstream breaks.  `[script-no-error-handling]` — ALWAYS_BLOCK.

- **No inline secrets.** Read credentials from Keychain (`security
  find-generic-password`) or environment (`os.environ`). Never
  inline an API key, even commented-out.
  `[script-secrets-inline]` — ALWAYS_BLOCK.

- **Event emission.** Cron scripts should `append_event(...)` to
  `events.db` on completion (and on failure). The framework's
  observability — and Sentinel's heartbeat-watch — depends on this.

`agency scaffold-script` generates a compliant skeleton.

### 5.5. Artifact lifecycle (T1 / T2 / T3)

- **T1 — Spike.** New idea, short-lived, exploratory. Audit applies
  warn-only. Promotion to T2 requires the audit to pass at strict.
- **T2 — Active.** Run in production for the deployment. Full audit
  applies; ALWAYS_BLOCK findings block promotions.
- **T3 — Promoted.** Earned higher autonomy. Same rules as T2 but
  the graduation gate applies more inputs (recapture, firing
  fidelity).

When you build, default to T1. Promote when you have data.

### 5.6. The no_agent cron pattern

A **critical architectural pattern** learned from v7 the hard way.

**Two cron shapes exist in HermesAgency:**

1. **Agent-driven cron** — fires a prompt that an LLM agent
   interprets and acts on. Used when the work is genuinely
   open-ended (drafting, classifying, multi-step reasoning).

2. **`no_agent` cron** — fires a self-contained script. The script
   handles the entire decision loop deterministically. It MAY call
   an inference API as a TOOL (for content generation, classification
   sub-tasks), but the LLM never has write authority to DBs, mail,
   kanban, or any other state.

**When to use `no_agent`:**

- Workflows with state that must not be corrupted (book coaching
  progress, financial records, anything appended to long-running
  tables)
- Workflows where the steps are deterministic even when the content
  is generative (e.g. "every 60m: poll inbox → classify each msg →
  for each unanswered question, generate next batch → store →
  send")
- Workflows where an LLM "getting creative" would cost real money
  or relationships (sending mail, deleting data, changing contracts)

**Why this matters (v7's lesson):** v7's prior book-coaching
architecture was the two-step shape: cron emits signals → LLM cron
agent interprets them → takes actions. The LLM:

- Deleted Q&A history when it thought it was "cleaning up"
- Generated questions with fresh batch numbers, overwriting state
- Sent emails to authors without authorization
- Made the system unrecoverable without manual DB inspection

The fix was structural: rewrite the cron as a `no_agent` script
that owns DB writes + mail authority and calls the LLM only as a
tool for question generation. **The LLM became the wordsmith; the
script stayed the boss.** Net effect: zero state-corruption
incidents since.

**How to declare `no_agent` in jobs.json:**

```json
{
  "name": "coach-method",
  "script": "/Users/ajc/.agency/profiles/libra/scripts/coach-method.py",
  "no_agent": true,
  "schedule": {"kind": "interval", "minutes": 60}
}
```

Hermes' scheduler honors the flag — it runs the script via the
operating system and never wraps it in an LLM agent loop.

**Pattern checklist for any `no_agent` script you write:**

- [ ] Script has shebang + try/except + error events
  (`script-no-error-handling` rule)
- [ ] Script holds DB write + side-effect authority (mail, files)
- [ ] Inference is called as a tool, never given side-effect handles
- [ ] Every decision branch is deterministic code, not LLM judgment
- [ ] Emits heartbeat at end of every run (so Sentinel can see it
  alive)
- [ ] Records firings for any learning rule that shaped a decision

The framework's `_framework/coaching/` subsystem is the reference
example. The full coach-method script template is at
`templates/scripts/coach-method.py`.

---

## 6. Profile creation

`agency scaffold-profile --role <role> --id <id>` is the canonical
path. It creates the directory tree, copies `SOUL.md.template` and
`standards.md.template` from `templates/profiles/<role>/`, and
substitutes placeholders.

Required files in any profile:

- **`SOUL.md`** — identity, voice, persona.  `[profile-missing-soul]`
  — ALWAYS_BLOCK.
- **`standards.md`** — quality floor.  `[profile-missing-standards]`
  — warn (allowed but risky).
- **`role.txt`** — the role id; the audit's role-mismatch detector
  reads this.
- **`config.yaml`** — model/provider overrides (optional).
- **`skills/`** — at least one starter skill.

`SOUL.md` and `standards.md` are **always-injected** at skill-load
time. Whatever is in them is part of every prompt this profile
runs. Treat them like load-bearing docs: edit deliberately, version
your edits, audit yourself for tone consistency.

---

## 7. Cross-profile work (kanban tenants)

When work crosses profile boundaries, the kanban is the channel.
Tenants (the `tenant` field on a task) categorize the work:

| Tenant | Use |
|---|---|
| `dossier` | Analyst Judge → CoS: research deliverable |
| `red-team` | Analyst Judge ← anyone: review a draft |
| `cross-profile-msg` | Agent-to-agent coordination |
| `bizdev` | BD pipeline tasks |
| `book-coaching` | Author task flow through Writing |
| `audit` | Audit findings → operator |
| `audit-confirm` | Operator → confirmed audit acks |
| `spec-review` | Spec/PR review |
| `alert` | Sentinel-filed warnings |
| `compliance` | Sentinel-filed weekly digest |
| `recapture` | Sentinel-filed recapture alerts |

Adding a tenant: PR to `_framework/invariants.yaml::kanban_tenants`.
Skill code should reference tenants by string but never hardcode the
list — let the audit catch references to unknown tenants.

**Link types matter.** Use `blocks` for true ordering dependencies
(child cannot proceed until parent done). Use `tracks` for soft
aggregation (parent shows status of children without gating).
Mixing them creates umbrella-deadlock — the parent waits on
children that wait on the parent. The framework's promoter ignores
`tracks` parents when computing readiness; `blocks` parents do
gate.

---

## 8. Path conventions

All paths derive from `_framework.constants`. Use them.

```python
from _framework.constants import (
    AGENCY_HOME, PROFILES_DIR, STATE_DIR,
    LEARNING_DB, KANBAN_DB, EVENTS_DB,
    profile_dir, profile_skills, profile_scripts,
    profile_soul, profile_standards,
)
```

Do not hardcode `/Users/...` paths. Do not write to `~/.loriah`
(deprecated path — audit warns). Do not put deployment-specific
content into `_framework/` (audit blocks via `framework-vendor-leak`
or related rules).

---

## 9. Audit rules (the 7-category taxonomy)

The audit reads `_framework/invariants.yaml::always_block_rules` and
`::warn_rules` as the canonical list. The 7 categories:

1. **Skill anatomy** — frontmatter, required sections
2. **Skill discipline** — verifier wired, supervised learning,
   action surface, untrusted-content, injection-trigger handling
3. **Script anatomy** — shebang, error handling, secrets
4. **Profile structure** — SOUL.md, standards.md, standards sources
5. **Cross-profile correctness** — role mismatch, tenant validity
6. **Learning loop wiring** — loop-broken, recapture implicates
   skill, untagged rules
7. **Framework integrity** — vendor leak, deprecated paths

Run:

```bash
agency audit                # whole deployment
agency audit --profile cos  # one profile
agency audit --skill draft-composer --profile cos  # one skill
agency audit --self         # framework only (no deployment needed)
agency audit --strict       # ALWAYS_BLOCK only — what graduation gate sees
```

### 9.5. Audit cadence + the graduation gate

- **On-edit (T1):** focused audit on the changed artifact.
- **Pre-promotion:** strict audit on the candidate skill. If any
  ALWAYS_BLOCK fires, promotion blocks until the issue is fixed.
- **Weekly (Sunday):** Sentinel runs full-fleet audit; results land
  in `_health/audits/` and the compliance report.

The graduation gate is the same audit invocation, just with
`--strict` and `--skill X --profile P`. There's nothing magic — the
gate runs what `agency audit` runs.

---

## 10. Versioning + change log

This playbook is versioned. The version in the header tracks the
framework version it ships against; minor playbook updates that
don't change rule shapes bump the playbook patch number without
needing a framework bump.

Adding an audit rule: bump playbook MINOR. Removing or weakening a
rule: bump MAJOR (it's a soft compatibility break for existing
deployments that pass the prior rule).

### Change log

- **2.0.0 (2026-05-23)** — extracted from v7's `DEVELOPMENT_PLAYBOOK.md`
  v1.1.0. Brand-references removed. Generalized for framework
  distribution. Categories renumbered to match `invariants.yaml`
  structure.

---

## 11. Deferred items (v0.2+)

Things the playbook will eventually formalize but isn't yet:

- **Cost/token attribution** — per-skill cost tracking + budget
  ceilings.
- **Synthetic edge-case battery** — generate adversarial test cases
  from accumulated exemplars (per Appendix A.2 of the spec).
- **Content-creation pipeline** — exemplar → iteration → diff
  calibration loop for production skills.
- **Multi-machine deployment** — when there's a second machine,
  the path conventions and the kanban-channel patterns extend
  unchanged; the deploy + sync story formalizes here.
- **Multi-tenant deployment** — multiple owners on one deployment.
  Far-future.
