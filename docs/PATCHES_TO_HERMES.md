# Patches to Hermes

HermesAgency layers on top of NousResearch's Hermes engine without
forking it. Three small patches to upstream Hermes are necessary
for the framework to function fully. These live in
`_framework/*_patches/` and reapply after each Hermes update via
the post-update reapply hook.

This document is the canonical list. If you're upgrading Hermes
and something seems broken, walk through these.

## Why no fork

Forks rot. The Hermes project moves; a fork that's a month behind
develops integration debt that compounds. The post-update reapply
pattern keeps the framework current with upstream automatically.

The patches are small (tens of lines, mostly hook insertions).
Reapplying them after a `pip install --upgrade hermes-agent` takes
the post-install hook seconds.

## Patch 1 — Learning-rule injection hooks

**Where:** `agent/skill_commands.py::_build_skill_message` and
`tools/skills_tool.py::skill_view`.

**Why:** Every skill load in Hermes calls one of these functions to
assemble the skill's system prompt. HermesAgency needs to insert
the applicable learning rules into that prompt before the model
sees it. Without this hook, captured corrections never reach the
model.

**What it does:** Calls
`_framework.learning.inject_for_skill(skill_name=..., profile=...,
role=..., voice_tags=...)` and appends the returned markdown to the
assembled prompt.

**Falls back:** If `_framework` isn't importable, returns the
prompt unmodified (the patch is degradation-safe).

**Upstream plan:** PR to NousResearch — a generic
"skill-load extensibility hook" that any framework layering on
Hermes can use. Until then, the patch lives in
`_framework/learning_patches/`.

## Patch 2 — Two kanban link types

**Where:** `kanban/kanban_db.py` — schema migration + the promoter
logic.

**Why:** v7 ran into an umbrella-deadlock: a parent task gets
linked to child tasks intending the relationship as
"tracking/aggregation," but the kanban's promoter treats every link
as gating completion. Parent waits on children; children wait on
parent if they were created as sub-tasks of the parent.

**What it does:**
- Adds a `link_type` column (`blocks` | `tracks`) to the
  `task_links` table
- Updates the promoter logic to only consider `blocks` parents
  when computing readiness
- Adds a migration that defaults existing links to `blocks` (the
  prior universal behavior)

**Falls back:** Old schema continues working — the patch is
additive. Skills that don't know about `link_type` see the prior
behavior on a `tracks` link (no gating), which is correct.

**Upstream plan:** PR to NousResearch — the umbrella-deadlock is a
real bug in the prior single-type model. Until merged, the patch
lives in `_framework/kanban_patches/`.

## Patch 3 — In-gateway cron flag

**Where:** `gateway/cron_runner.py` (or wherever cron firing is
gated).

**Why:** When the framework is in maintenance / upgrade mode, the
operator wants to pause cron firing without stopping the gateway.
A single environment variable (`HERMES_INGATEWAY_CRON=off`)
short-circuits the cron loop while leaving the rest of the gateway
responsive (so the operator can investigate via dashboard, kanban,
etc.).

**What it does:** Adds an env-var check at the top of the cron
firing function; when set to "off", logs a single line per cycle
and skips firing. Default is unset → fire normally.

**Falls back:** If the env var is unset (the default), behavior is
identical to upstream. The patch only changes behavior when the
operator explicitly opts in.

**Upstream plan:** PR to NousResearch as a small, clearly-named
operational toggle. Until then, lives in
`_framework/gateway_patches/`.

## Post-update reapply hook

The framework includes a post-update script that:

1. Detects whether Hermes was updated since last invocation
2. If yes: copies the patches from `_framework/*_patches/` into
   the freshly-installed Hermes source
3. Validates the patches still apply cleanly to the new Hermes
   source
4. If any patch fails: surfaces a kanban alert (`tenant=alert`)
   describing which patch failed and against which Hermes version

If patches stop applying cleanly (which would happen if upstream
heavily refactors the patched files), the framework still boots —
but the corresponding feature is degraded. The alert tells the
operator that upgrading the framework is needed before that feature
returns.

Run manually:

```bash
python -m _framework.ops.reapply_hermes_patches    # v0.2 deliverable
```

In v0.1, patches are documented but the auto-reapply script
itself is part of the v0.2 build. For v0.1 deployments, apply the
patches by hand against the operator's Hermes install — or skip
them and accept the degraded behavior (injection won't run,
two-link-type kanban won't work, in-gateway cron flag won't
respond).
