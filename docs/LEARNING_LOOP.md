# The learning loop — the spine

HermesAgency's central promise is the seven-step learning loop.
Everything else is in service of it.

> Every correction the owner gives is captured, tagged, propagated to
> every relevant agent across the agency, and applied without the
> owner repeating themselves.

If you break any link in this chain, the owner is repeating
themselves — and the framework's value proposition is broken.

---

## The seven steps

### 1. Capture

`_framework/learning/correction_capture.py::capture_correction()` is
the entry point. Every owner correction lands here, regardless of
source (kanban comment, email, chat, CLI):

```python
from _framework.learning import capture_correction

result = capture_correction(
    correction="Lead with craft, not metrics.",
    source="chat:session-42:turn-7",
    skill_tags=["draft-composer"],
    role_tags=["chief-of-staff"],
    voice_tags=["warm-not-flattering"],
    is_hard=False,
)
# result.rule_id  → stable hash of (correction, source)
# result.recapture → set if this matches a prior rule
```

Convenience wrappers exist for the common capture paths:

- `capture_from_kanban_comment(task_id, text, ...)` — owner replied
  to a kanban task with a correction
- `capture_from_inbox(message_id, classification, text, ...)` —
  email contained a directive
- `capture_from_chat(session_id, turn, text, ...)` — interactive

All paths flow through the same core so recapture detection sees
everything.

### 2. Tag

Three axes:

- **`skill_tags`** — kebab-case skill names. At least one required.
  Special value `general` means "applies across all skills."
- **`role_tags`** — kebab-case role names from
  `invariants.yaml::roles`. Used for cross-agent rules (e.g.
  voice/style rules that apply to anyone speaking for the owner).
- **`voice_tags`** — free-form attributes like `firm`,
  `warm-not-flattering`, `we-not-i`. Skills declare which voice
  tags apply via frontmatter.

A rule tagged `[skill-foo, general]` injects everywhere. A rule
tagged `[role:chief-of-staff]` injects in every CoS skill. A rule
tagged `[voice:we-not-i]` injects wherever drafting happens.

### 3. Inject

`_framework/learning/rule_injection.py::inject_for_skill()` runs at
skill-load:

```python
from _framework.learning import inject_for_skill

text = inject_for_skill(
    skill_name="draft-composer",
    profile="loriah",
    role="chief-of-staff",
    voice_tags=["we-not-i", "warm-not-flattering"],
    cap=20,
)
# text is a markdown block to append to the skill's prompt
```

Resolution:
1. Pull rules where `skill_tags` includes this skill
2. UNION rules where `'general' in skill_tags`
3. UNION rules where `role_tags` includes this profile's role
4. UNION rules where `voice_tags` overlap this skill's declared voice
5. Order by `(is_hard DESC, last_fired_at DESC, created_at DESC)`
6. Cap at `cap` rules (default 20)

Hermes wires this into its skill-load via patches to
`agent/skill_commands.py::_build_skill_message` and
`tools/skills_tool.py::skill_view`. Patches reapply after each
Hermes update via the post-update hook
(see [`PATCHES_TO_HERMES.md`](PATCHES_TO_HERMES.md)).

### 4. Apply

The model uses the injected rule in its next decision. This step is
the model's responsibility — the framework can't enforce it
directly. What the framework CAN do:

- Inject the rule prominently (hard rules first, then most-recently-
  fired, then most recent)
- Document the firing-record requirement in every skill (the
  scaffold inserts a self-check step)
- Detect when a rule was injected but no firing was recorded over
  many invocations — that's a "loop broken in step 4" signal the
  weekly compliance report surfaces

### 5. Record

`_framework/learning/firings.py::record_firing()` is called by the
skill when a rule shapes a decision:

```python
from _framework.learning import record_firing

record_firing(
    rule_id="abc123",
    skill_tag="draft-composer",
    profile="loriah",
    action_summary="held draft for owner review because rule X said so",
    was_overridden=False,  # True if a hard rule was violated
)
```

Hard rules also record via the send-guard / verifier when they
catch a violation attempt — `was_overridden=True` flags the breach
so the recapture detector and graduation gate see it.

### 6. Detect re-correction

`_framework/learning/recapture_detector.py::check_recapture()` runs
inline inside `capture_correction()`. When a new correction's
embedding is too similar (default threshold: cosine 0.85) to any
active rule from the last 90 days using the same embedding model:

- Row appended to `recapture_events`
- Sentinel's `learning_monitor` cron sees it and emits a
  `recapture_detected` event
- The responsible skill demotes (see step 7)

Owner can mark a recapture as false-positive via the alert kanban
task. The detector adds the (rule_a, rule_b) pair to
`recapture_denylist` and excludes them from future alerts.

### 7. Escalate

When recapture fires:

- A kanban task lands in the operator's queue with the full
  context (which two rules, what similarity, which skills)
- The implicated skill demotes one level
  (`autonomy.failure` event with reason `recapture: similarity=0.91`)
- The graduation gate refuses to promote the skill until the
  recapture is dismissed or the underlying issue is fixed (parking
  the counter at threshold)

---

## What it takes to keep the loop working

The framework's audit (`agency audit`) enforces structural
preconditions for each link:

- **Capture wire** — every correction-receiving skill calls
  `capture_correction()` or one of its wrappers. Missing wire =
  no capture = no learning.
- **Injection wire** — every skill loads applicable rules into its
  prompt at skill-load time. `skill-no-supervised-learning`
  ALWAYS_BLOCK rule catches missing wire.
- **Firing wire** — every skill records firings for the rules it
  used. `learning-loop-broken` ALWAYS_BLOCK rule fires when a
  skill has >3 captured rules and 0 firings in 30 days.
- **Tag accuracy** — `learning-rule-untagged` warn rule catches
  rules with only `general` tag (likely under-targeted).

The weekly compliance report (`_framework/learning/compliance_report.py`)
produces a Sunday-morning summary the operator reads to verify the
loop is still functioning:

- Rules captured this week
- Rules fired most (top 8 + override rate)
- Recapture events (each is a system-failure flag)
- Rules never fired in 90 days (likely dead or mis-tagged)
- Top 5 skills by firings (where the loop is most active)
- Top 5 skills with >3 rules and 0 firings (where the loop is broken)

---

## The CLI surface

```bash
agency capture "your correction here" \
    --skill draft-composer --role chief-of-staff \
    --voice we-not-i

agency learn list                  # most recently captured rules
agency learn show <rule_id>        # one rule + firings history

agency events --kind recapture_detected  # check for system-failure flags
```

---

## Embedding model

`_framework/learning/embeddings.py` defines an `Embedder` protocol.
The default is a `HashEmbedder` — deterministic bag-of-words
hashing with 256 dimensions. It works without external dependencies
and makes the framework boot on a clean machine, but it is **not
semantically meaningful**: two paraphrases of the same idea may land
in different buckets if they share no exact tokens.

Operators wire a real embedding backend for production deployments.
Recommended: sentence-transformers, OpenAI-compatible embedding
endpoints, Ollama embed, local HF models, etc. The framework treats
them all as opaque `Embedder` implementations.
