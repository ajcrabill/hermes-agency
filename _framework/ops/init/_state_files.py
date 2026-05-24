# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Helper: ensure operational-state.md and conversation-journal.md exist
in state-vault on first init. Tier 3 calls this after the interview.
"""

from __future__ import annotations

from datetime import datetime

from _framework.constants import (
    CONVERSATION_JOURNAL_MD,
    OPERATIONAL_STATE_MD,
    STATE_VAULT,
)


def ensure_initial_state_files(owner_name: str = "", interview_date: str = "") -> None:
    STATE_VAULT.mkdir(parents=True, exist_ok=True)
    interview_date = interview_date or datetime.now().strftime("%Y-%m-%d")

    if not OPERATIONAL_STATE_MD.exists():
        OPERATIONAL_STATE_MD.write_text(
            f"""# operational-state — durable cross-session memory

_Created from Tier 3 interview on {interview_date}._

This file is the agency's persistent operational memory. It survives
across sessions and process restarts. Hermes' learning-rule injection
reduces dependency on this file — but where the rule-axis doesn't
fit (infrastructure status, ongoing project status, recent operator
decisions, known bugs), this is the canonical record.

Read at session start. Updated when formal triggers fire (see Update
Protocol below). Pruned regularly so it doesn't bloat.

## Infrastructure status

_(Current health of agency components. Updated by Sentinel's
weekly compliance report; reviewed by CoS at session start.)_

- All agents: status unknown until first Sentinel run
- Last full audit: pending first run
- Last compliance report: pending first run

## Active delegations

_(Tasks the principal delegated to agents. Kanban is the source of
truth; this file aggregates open delegations for fast read.)_

(none yet — `agency kanban list --assignee aj` populates this)

## Ongoing projects

_(Multi-week / multi-month efforts and where they stand. Updated by
the agent who owns each project; CoS aggregates weekly.)_

(none yet — populated as projects start)

## Recent operator decisions

_(Decisions the principal made that change how the agency operates.
Last 10. Older entries archive to learning-rules.)_

(none yet — populated as decisions land)

## Known issues

_(Open bugs, broken integrations, deferred work. Each entry has a
kanban task id.)_

(none yet)

---

## Update Protocol

Update this file when:
1. A new project starts or completes (`Ongoing projects` section)
2. The principal makes a structural decision (`Recent operator decisions`)
3. An issue is discovered or resolved (`Known issues`)
4. Weekly: Sentinel updates `Infrastructure status`

Pruning: every quarter, archive entries older than 90 days to
`state-vault/archive/operational-state-{{YYYY-MM-DD}}.md`.
""",
            encoding="utf-8",
        )

    if not CONVERSATION_JOURNAL_MD.exists():
        CONVERSATION_JOURNAL_MD.write_text(
            f"""# conversation-journal — in-progress thinking

_Created from Tier 3 interview on {interview_date}._

This is the rolling memory of conversations in progress. Where
operational-state.md tracks formal outcomes (decisions made,
projects started), this tracks the in-between — brainstorming
threads, half-formed ideas, evolving decisions that haven't hit a
formal trigger yet.

If a new session starts and the conversation was mid-flight, this
is the file that lets the new session pick up the thread.

## Active discussion threads

_(Ongoing conversations with the principal that haven't produced a
formal outcome yet. Each entry: topic, latest state, what we're
waiting on.)_

(none yet — populated during active conversations)

## Recent brainstorms

_(Half-formed ideas worth remembering. Most won't go anywhere; some
will become projects or decisions. Last 5-10.)_

(none yet)

## Open questions to {{OWNER_NAME}}

_(Things an agent wanted to ask but parked. Surfaced at the next
appropriate touch-point.)_

(none yet)

---

## Update Protocol

Update this file when:
- A multi-turn conversation produces new context worth remembering
- An idea floats by that's worth capturing but isn't yet a decision
- An agent has a question to surface later

Pruning: weekly, move entries older than 14 days that didn't
produce an outcome to `state-vault/archive/conversation-journal-{{YYYY-MM-DD}}.md`
or convert them to learning rules.
""".replace("{{OWNER_NAME}}", owner_name or "the principal"),
            encoding="utf-8",
        )


__all__ = ["ensure_initial_state_files"]
