# PLUGIN — owned by HermesAgency. Registered into Hermes via plugin.yaml.
"""
Hermes lifecycle hooks that wire HermesAgency's reliability systems
into Hermes' execution path.

Each hook is fail-open: an exception in a hook is logged but never
breaks Hermes. The PluginManager's invoke_hook() already wraps each
callback in try/except — but we add a second layer here, because a
malformed deployment.yaml (or empty learning.db) shouldn't even
log warnings; it should silently let Hermes proceed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── pre_llm_call: inject applicable learning rules ─────────────────────


def on_pre_llm_call(
    session_id: str = "",
    user_message: str = "",
    is_first_turn: bool = False,
    **_: Any,
) -> Optional[Dict[str, str]]:
    """Inject applicable learning rules into the current turn's context.

    Returns a dict `{"context": markdown}` — Hermes appends that to
    the USER message (not system prompt — preserves prompt cache).

    This is the #1 reliability system: the supervised learning loop's
    INJECT step. Replaces v0.2-v0.16's source-tree text-anchor patch.
    """
    try:
        from _framework.learning import inject_for_skill
        from .context import current_profile_and_role

        profile, role = current_profile_and_role()
        if not profile:
            return None

        rules_md = inject_for_skill(
            skill_name="interactive-chat",   # synthetic skill for free-form chat
            profile=profile,
            role=role,
        )
        if not rules_md:
            return None
        return {"context": rules_md}
    except Exception as e:
        logger.debug("hermes-agency pre_llm_call hook skipped: %s", e)
        return None


# ── pre_tool_call: autonomy gate + send-guard ──────────────────────────


# Tools that send mail to the outside world. Send-guard fires before
# these. (Conservative list; Hermes mail tools may be named differently
# in a given deployment — extend per integration.)
_OUTBOUND_MAIL_TOOLS = frozenset({
    "send_email",
    "gmail_send",
    "email_send",
    "compose_and_send",
})

# Action-class mapping by Hermes tool name. The autonomy ladder gates
# on action class. Tools not in this map default to "draft" (the
# safest middle ground — let Hermes' own approval flow handle it).
_TOOL_ACTION_CLASS: Dict[str, str] = {
    # Read-only — always allowed, ungated
    "read_file": "read",
    "list_files": "read",
    "search_files": "read",
    "search": "read",
    # Writes to user state
    "write_file": "structural-change",
    "patch": "structural-change",
    "edit_file": "structural-change",
    # External / send
    "send_email": "send-batched",
    "gmail_send": "send-batched",
    "email_send": "send-batched",
    "compose_and_send": "send-batched",
    # Destructive
    "delete_file": "auto-irreversible",
    "rm": "auto-irreversible",
    # Shell access
    "terminal": "structural-change",
    "execute_code": "structural-change",
}


def on_pre_tool_call(
    tool_name: str = "",
    args: Optional[Dict[str, Any]] = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    **_: Any,
) -> Optional[str]:
    """Return a block message (string) to refuse the tool call;
    return None to allow it.

    Wires two reliability systems:
      #2 Autonomy ladder — refuses tool calls outside the current
         skill's earned autonomy level
      #6 Send-guard — for outbound-mail tools, runs send-guard.evaluate
         before allowing the send
    """
    try:
        action_class = _TOOL_ACTION_CLASS.get(tool_name, "draft-only")

        # Read-only tools always allowed
        if action_class == "read":
            return None

        from .context import current_profile_and_role
        profile, _role = current_profile_and_role()
        if not profile:
            return None   # no deployment configured yet — don't gate

        # Autonomy gate
        block = _autonomy_check(profile, tool_name, action_class)
        if block is not None:
            return block

        # Send-guard for outbound mail
        if tool_name in _OUTBOUND_MAIL_TOOLS:
            block = _send_guard_check(profile, args or {})
            if block is not None:
                return block

        return None
    except Exception as e:
        logger.debug("hermes-agency pre_tool_call hook skipped: %s", e)
        return None


def _autonomy_check(profile: str, tool_name: str, action_class: str) -> Optional[str]:
    """Compose autonomy.get_skill_level + get_action_class_min_level
    to decide whether the skill is authorized to take this action."""
    try:
        from _framework.autonomy import get_skill_level, get_action_class_min_level
    except ImportError:
        return None
    try:
        # Use "interactive-chat" as the synthetic skill for free-form
        # Hermes conversations; once Hermes-side skill context is
        # plumbed through in v0.18, replace with the real skill id.
        skill = "interactive-chat"
        current_level = get_skill_level(skill, profile)
        required_level = get_action_class_min_level(action_class)
        if current_level >= required_level:
            return None
        return (
            f"[HermesAgency autonomy gate] Tool '{tool_name}' is in "
            f"action class '{action_class}' which requires L{required_level}+; "
            f"skill '{skill}' is currently at L{current_level}. "
            f"Route this through the kanban for operator approval, "
            f"or promote the skill via `agency promote --skill {skill} "
            f"--profile {profile}`."
        )
    except Exception as e:
        logger.debug("autonomy check error: %s", e)
        return None


def _send_guard_check(profile: str, args: Dict[str, Any]) -> Optional[str]:
    """Construct a SendCandidate from the tool args and run send-guard."""
    try:
        from _framework.send_guard import evaluate, SendCandidate
    except ImportError:
        return None
    try:
        to_val = args.get("to") or args.get("recipient") or args.get("to_email") or ""
        if isinstance(to_val, str):
            to_list = [t.strip() for t in to_val.split(",") if t.strip()]
        elif isinstance(to_val, list):
            to_list = [str(t).strip() for t in to_val if str(t).strip()]
        else:
            to_list = []
        if not to_list:
            return None   # nothing to check; let Hermes return its own error

        cand = SendCandidate(
            to=to_list,
            subject=str(args.get("subject") or ""),
            body=str(args.get("body") or args.get("text") or args.get("message") or ""),
            profile=profile,
            skill="interactive-chat",
        )
        decision = evaluate(cand)
        if decision.allowed:
            return None
        reason_str = "; ".join(decision.reasons) if decision.reasons else "policy denied"
        return (
            f"[HermesAgency send-guard] Outbound mail refused: {reason_str}. "
            f"Edit `~/.hermes/agency-state/email-access.md` (access list), wait for the "
            f"cooling period, or override via the operator-approval path."
        )
    except Exception as e:
        logger.debug("send-guard check error: %s", e)
        return None


# ── post_tool_call: observation (verifier enforcement runs in transform_tool_result) ──


def on_post_tool_call(
    tool_name: str = "",
    args: Optional[Dict[str, Any]] = None,
    result: Any = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    duration_ms: int = 0,
    **_: Any,
) -> None:
    """Observational tool-completion logger. v0.17 records every tool
    completion to events.db so Sentinel/audit can see them.

    v0.18 adds the verifier policy: for each completed skill action,
    run the active skill's frontmatter verifier criteria against the
    output; on failure, escalate via `transform_tool_result` so the
    LLM sees the failure as an actionable error.

    Wires reliability system #3 (Verifier) — observation in v0.17,
    enforcement in v0.18.
    """
    try:
        from _framework.sentinel import append_event
        from .context import current_profile_and_role

        profile, _ = current_profile_and_role()
        append_event(
            kind="tool_completed",
            actor=profile or "hermes",
            target=tool_name,
            severity="info",
            payload={
                "duration_ms": duration_ms,
                "task_id": task_id,
                "session_id": session_id,
            },
        )
    except Exception as e:
        logger.debug("hermes-agency post_tool_call hook skipped: %s", e)


# ── transform_tool_result: verifier enforcement ────────────────────────


# Tools that produce a verifiable filesystem artifact. The verifier
# constructs an ad-hoc criterion for each — `file_exists` for writes,
# `file_contains` for patches — and rewrites the tool result with an
# actionable error message if the criterion fails.
#
# v0.18 ships generic tool-output verification. v0.21 will add per-
# skill context awareness once Hermes' agentskills.io integration
# exposes "which skill is currently running" to plugin hooks.
_VERIFIABLE_WRITE_TOOLS = frozenset({"write_file", "patch", "edit_file"})


def on_transform_tool_result(
    tool_name: str = "",
    args: Optional[Dict[str, Any]] = None,
    result: Any = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    duration_ms: int = 0,
    **_: Any,
) -> Optional[str]:
    """Run verifier criteria against the tool result. Returns a
    rewritten result string (Hermes uses the first valid-string return)
    OR None to leave the result unchanged.

    Wires reliability system #3 (Verifier) as load-bearing: a tool that
    claims success but produces no actual filesystem artifact (or
    produces a malformed one) gets its result rewritten into an
    actionable error the LLM can see and act on.
    """
    try:
        if tool_name not in _VERIFIABLE_WRITE_TOOLS:
            return None
        if not isinstance(args, dict):
            return None

        criteria = _criteria_for_tool(tool_name, args)
        if not criteria:
            return None

        from _framework.verifier import check
        v_result = check(criteria)
        if v_result.passed:
            return None

        # Rewrite the result with a clear error the LLM can act on.
        failures = []
        for f in v_result.failures:
            failures.append(f"  - {f.type}: {f.message}")
        failures_str = "\n".join(failures) if failures else "  (no detailed failures recorded)"

        rewritten = (
            f"[HermesAgency verifier — TOOL OUTPUT FAILED VERIFICATION]\n\n"
            f"Tool '{tool_name}' returned success, but the verifier "
            f"caught {len(v_result.failures)} criterion failure(s):\n\n"
            f"{failures_str}\n\n"
            f"Original tool result (for debugging):\n"
            f"{_truncate(str(result), 400)}\n\n"
            f"Either fix the issue and re-run the tool, or explain in your "
            f"response why this failure is acceptable for the task."
        )
        return rewritten
    except Exception as e:
        logger.debug("hermes-agency transform_tool_result hook skipped: %s", e)
        return None


def _criteria_for_tool(tool_name: str, args: Dict[str, Any]) -> list[dict]:
    """Construct ad-hoc verifier criteria for a tool call based on its
    args. v0.18 generic criteria; v0.21 will replace with per-skill
    criteria pulled from the active skill's frontmatter."""
    path = args.get("path") or args.get("file_path") or args.get("target")
    if not path or not isinstance(path, str):
        return []

    if tool_name == "write_file":
        return [{"type": "file_exists", "args": {"path": path}}]

    if tool_name in ("patch", "edit_file"):
        # If the args carry a `content` or `new_string`, verify that
        # text now appears in the target. Otherwise just verify the
        # file still exists (the patch didn't delete it).
        new_content = (
            args.get("new_string")
            or args.get("content")
            or args.get("replacement")
        )
        if isinstance(new_content, str) and new_content.strip():
            # Only the first 80 chars of the expected content — a
            # reasonable substring check that doesn't fail on whitespace
            # normalization.
            needle = new_content.strip()[:80]
            return [
                {"type": "file_exists", "args": {"path": path}},
                {"type": "file_contains", "args": {"path": path, "needle": needle}},
            ]
        return [{"type": "file_exists", "args": {"path": path}}]

    return []


def _truncate(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + "..."


# ── on_session_start / on_session_end: Sentinel observation ────────────


def on_session_start(
    session_id: str = "",
    model: str = "",
    platform: str = "",
    **_: Any,
) -> None:
    """Sentinel observation point — record session open."""
    try:
        from _framework.sentinel import append_event
        append_event(
            kind="session_started",
            actor="hermes",
            target=session_id,
            severity="info",
            payload={"model": model, "platform": platform},
        )
    except Exception as e:
        logger.debug("hermes-agency on_session_start hook skipped: %s", e)


def on_session_end(
    session_id: str = "",
    completed: bool = True,
    interrupted: bool = False,
    **_: Any,
) -> None:
    """Sentinel observation point — record session close."""
    try:
        from _framework.sentinel import append_event
        append_event(
            kind="session_ended",
            actor="hermes",
            target=session_id,
            severity="info" if completed else "warning",
            payload={"completed": completed, "interrupted": interrupted},
        )
    except Exception as e:
        logger.debug("hermes-agency on_session_end hook skipped: %s", e)


__all__ = [
    "on_pre_llm_call",
    "on_pre_tool_call",
    "on_post_tool_call",
    "on_transform_tool_result",
    "on_session_start",
    "on_session_end",
]
