# Autonomy — the L1-L5 ladder

Every skill in HermesAgency starts at **L1 draft-only** and earns
its level. Promotion is structurally gated; demotion happens on
any failure signal.

## The five levels

| Level | Id | Description |
|---|---|---|
| **L1** | `draft-only` | Drafts everything, sends nothing. The starting level for every skill. |
| **L2** | `send-batched` | Sends in supervised batches; owner reviews the queue. |
| **L3** | `send-single` | Sends single items, notifies the owner. |
| **L4** | `structural-change` | Modifies DB rows, archives tasks, structural operations. |
| **L5** | `auto-irreversible` | Auto-send to new contacts, delete data, anything not on a hard ceiling. |

L1 is generous in what a skill is allowed to *produce*; it's L1 in
what it's allowed to *do without supervision*. Most skills can ship
useful work at L1 forever.

## The action gate

Before any consequential action, the skill runs through the action
gate (`_framework/autonomy/autonomy_gate.sh`):

```bash
autonomy_gate.sh <skill> <action-class> <profile>
# exit 0 = allowed; exit 1 = denied
```

The gate checks: does this skill have authority for this action
class at its current level? `draft-only` needs L1; `send-batched`
needs L2; etc. Per `invariants.yaml::action_classes`.

Denials emit a `send_blocked` event and file a kanban task — the
operator sees them.

## The three-input promotion gate

L→L+1 requires **all three** inputs to pass:

### 1. Track record

`N` consecutive `clean_run` events. Default `N=5`. A `clean_run`
event is recorded by the skill itself when it completes
successfully (verifier passed, no exceptions, no overrides).

### 2. Structural compliance

`agency audit --skill X --profile P --strict` returns 0. No
ALWAYS_BLOCK findings remain on this skill.

The audit checks anatomy (frontmatter, verifier wired, supervised
learning, action surface, untrusted content if applicable),
discipline (no quoted injection triggers), and learning-loop
integrity (rules captured under this skill have firings).

### 3. Learning fidelity

Two sub-checks:

- **No recapture events implicating this skill in the last 14 days.**
  If the owner has had to repeat a correction this skill is
  responsible for in the last two weeks, promotion blocks.

- **Firing pulse.** If the skill has >3 captured learning rules, it
  has >0 firings in the last 30 days. A skill that's accumulating
  corrections without applying any is a broken loop.

When the gate blocks, the failure mode is recorded in
`skill_autonomy_history` as either `audit_blocked_promote` or
`learning_blocked_promote`. The counter is **parked** at threshold —
the next clean_run after the issue is fixed retries promotion
automatically.

## Demotion

Any single failure signal demotes:

- **Failed run.** `agency demote <skill> --profile P --reason verifier-failed`
  or the engine's `record_event(kind='failure')`.
- **Recapture event implicating the skill.** Inline demotion at
  recapture-detect time.
- **New ALWAYS_BLOCK finding.** When the audit detects a regression,
  the implicated skill demotes.

Demotion is always allowed — there's no gate. The point is: the
framework demotes generously to keep the bar high.

## Hard ceilings

Some actions are NEVER autonomous, regardless of level
(`invariants.yaml::hard_send_ceilings`):

- `never-autonomous-send-per-recipient` — per-recipient veto
- `new-contact-first-message` — first message to a new address
  always holds for review
- `blacklist-recipient` — anyone on the blacklist is a deny

These enforce at the send-guard layer, not at the autonomy gate.
A skill at L5 still has to clear hard ceilings; L5 only authorizes
the *class* of action.

## Action class taxonomy (composes with L1-L5)

Borrowed from `agent-core` (Appendix A.5 of spec). Orthogonal to
the level — describes what KIND of action regardless of who can do
it:

- **Autonomous:** read, write-internal, peer messages, calendar
  reads, ingest pipelines, exemplar capture
- **Gated (one-click human confirmation):** send external email,
  publish content, create external invite, install skill from catalog
- **Forbidden:** secret access, financial actions, modifying
  safety policies

The autonomy gate checks BOTH: (1) the action class allows; (2)
the skill's level meets the action class's minimum.

## CLI

```bash
agency promote draft-composer --profile loriah  # gated
agency demote  draft-composer --profile loriah  # ungated; always allowed
```

`agency promote` runs through the same three-input gate as a
clean_run-triggered promotion. The gate is the gate; manual
overrides are just another invocation of it.
