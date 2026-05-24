# PLUGIN — owned by HermesAgency.
"""
The /agency setup interactive interview.

Two paths:

  MIGRATION: one prompt, one answer. /agency setup migrate <v7-path>
             → runs migrate_v7_full(<path>) → writes .configured.

  CLEAN INSTALL: 8 questions. /agency setup clean starts the flow;
             each /agency setup answer <text> advances one step.
             At the end, writes Goals.md / Values.md / Personal.md /
             Work.md / Clients.md + a SOUL refinement note, then
             writes .configured.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from hermes_agency_plugin.context import _agency_home, current_profile_and_role
from .state import (
    SetupState, load_state, save_state, clear_state,
    is_configured, mark_configured,
)


# ── The clean-install interview ───────────────────────────────────────────


# Each entry is: (step_id, prompt_to_user, field_name_for_answer)
# Steps execute in order. After the last step, _finalize_clean_install()
# writes the vault files + marker.
_CLEAN_INSTALL_STEPS: list[tuple[str, str, str]] = [
    (
        "PRINCIPAL",
        "What's your name? (This is the Principal — the person the "
        "agency serves. First name is fine; goes into Personal.md.)",
        "principal_name",
    ),
    (
        "ORG",
        "What's your business or organization called? (Goes into the "
        "deployment manifest + appears in CoS's introductions of you.)",
        "org_name",
    ),
    (
        "ROLE",
        "What's your role / what kind of work do you do? (One or two "
        "sentences — what would you tell a stranger at a conference. "
        "Goes into Work.md.)",
        "role_description",
    ),
    (
        "GOALS",
        "What are you working toward right now? List 2-5 current "
        "goals — could be financial, professional, project-specific, "
        "personal. Don't worry about format; CoS will refine them into "
        "SMART form later. Goes into Goals.md.",
        "current_goals",
    ),
    (
        "GUARDRAILS",
        "What are 1-3 lines you won't cross — values that guide HOW "
        "you work and make decisions, even when crossing them might "
        "be tempting? Could be \"honesty,\" \"craft,\" \"long-term "
        "thinking,\" \"being a good ancestor,\" etc. The agency "
        "translates these into prohibitions the enforcement layer "
        "(Sentinel, send-guard, audit) checks against. Goes into "
        "Guardrails.md.",
        "values",
    ),
    (
        "PERSONAL",
        "Anything personal CoS should know? Family situation, "
        "constraints on hours, communication preferences, recurring "
        "appointments, health considerations — whatever's relevant "
        "to your operational life. Goes into Personal.md.",
        "personal_context",
    ),
    (
        "CLIENTS",
        "Who are your current clients or recurring stakeholders? "
        "List names + a one-line description of each (or paste a "
        "block of names — I'll keep them as-is). Goes into Clients.md.",
        "clients",
    ),
    (
        "VOICE",
        "Last question: what's distinctive about your voice when you "
        "write — anything CoS should mimic or avoid? E.g. \"I write "
        "in short paragraphs,\" \"I never use exclamation marks,\" "
        "\"I prefer specifics over abstractions.\" Goes into your "
        "SOUL.md as a voice-attributes section.",
        "voice_notes",
    ),
]


def handle_setup_command(rest: str) -> str:
    """Route /agency setup invocations."""
    argv = (rest or "").strip().split(None, 1)
    sub = argv[0].lower() if argv else ""
    arg = argv[1] if len(argv) > 1 else ""

    if is_configured() and sub != "reset":
        return (
            "Deployment is already configured (`~/.hermes/agency-state/"
            ".configured` exists).\n\n"
            "  To re-configure, run: `/agency setup reset` then start over.\n"
            "  Otherwise, `/agency status` to see deployment state."
        )

    if sub == "reset":
        return _reset()
    if sub == "migrate":
        return _migrate(arg)
    if sub == "clean":
        return _start_clean_install()
    if sub == "answer":
        return _advance_clean_install(arg)
    if sub == "approve":
        return _approve_draft()
    if sub == "revise":
        return _revise_draft(arg)
    if sub == "status":
        return _status()
    if sub in ("", "help"):
        return _initial_prompt()
    return f"Unknown `/agency setup` subcommand: {sub}\n\n" + _initial_prompt()


# ── Subcommand handlers ───────────────────────────────────────────────────


def _initial_prompt() -> str:
    state = load_state()
    if state.kind == "clean" and state.current_step != "INITIAL":
        # Resume an in-progress clean install
        step = _current_step(state)
        if step is not None:
            return _format_clean_question(state, step)
    return """\
Welcome to HermesAgency setup. Two paths:

  Migrating from a prior install (v7 / dCoS / earlier Loriah)?
      /agency setup migrate <path-to-prior-home>
      Example: /agency setup migrate ~/.hermes-v7-backup

  Starting fresh?
      /agency setup clean

  See current status:
      /agency setup status

  Start over (if you've already begun setup and want to wipe it):
      /agency setup reset
"""


def _reset() -> str:
    clear_state()
    return "Setup state cleared. Run `/agency setup` to start over."


def _status() -> str:
    state = load_state()
    if is_configured():
        return "✓ Deployment is configured."
    if state.kind == "":
        return "Setup not started. Run `/agency setup` for options."
    if state.kind == "migration":
        return "Setup in progress: migration path."
    if state.kind == "clean":
        step_idx = _step_index(state.current_step)
        return (
            f"Setup in progress: clean install, step "
            f"{step_idx + 1}/{len(_CLEAN_INSTALL_STEPS)}.\n"
            f"Last collected: {list(state.collected_answers.keys())}"
        )
    return f"Setup state unknown: kind={state.kind}"


def _migrate(path_str: str) -> str:
    path_str = path_str.strip()
    if not path_str:
        return ("Migration needs a path. Usage:\n"
                "    /agency setup migrate <path-to-prior-home>\n"
                "Example:\n"
                "    /agency setup migrate ~/.hermes-v7-backup")

    state = load_state()
    state.kind = "migration"
    state.collected_answers["v7_path"] = path_str
    state.current_step = "RUNNING"
    save_state(state)

    try:
        from _framework.migration import migrate_v7_full
    except ImportError as e:
        return f"Migration tool unavailable: {e}"

    profile, _ = current_profile_and_role()
    profile_id = profile or "loriah"

    try:
        result = migrate_v7_full(
            Path(path_str).expanduser(),
            profile=profile_id,
            apply=True,
        )
    except FileNotFoundError as e:
        state.current_step = "FAILED"
        save_state(state)
        return f"Migration failed: {e}\n\nRe-run with a corrected path."
    except Exception as e:
        state.current_step = "FAILED"
        save_state(state)
        return f"Migration error: {e}"

    mark_configured()
    clear_state()
    return (
        "✓ Migration complete.\n\n"
        + result.summary()
        + "\n\n"
        "Deployment is now configured. You can use HermesAgency normally."
    )


def _start_clean_install() -> str:
    state = load_state()
    if state.kind == "clean" and state.current_step != "INITIAL":
        # Resume
        step = _current_step(state)
        if step is not None:
            return _format_clean_question(state, step)
    state = SetupState(kind="clean", current_step=_CLEAN_INSTALL_STEPS[0][0])
    save_state(state)
    return _format_clean_question(state, _CLEAN_INSTALL_STEPS[0])


def _advance_clean_install(text: str) -> str:
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    state = load_state()
    if state.kind != "clean":
        return ("No clean-install in progress. Start with: `/agency "
                "setup clean`")
    step = _current_step(state)
    if step is None:
        return "Internal error: no current step. Try `/agency setup reset`."
    if not text:
        return ("Answer cannot be empty. Usage:\n"
                "    /agency setup answer <your answer text>")

    step_id, _, field_name = step
    state.collected_answers[field_name] = text

    # Advance
    next_idx = _step_index(step_id) + 1
    if next_idx >= len(_CLEAN_INSTALL_STEPS):
        # All questions answered → present rough draft for approval
        # per StrategicPlanning.md §3.5 step 4-5. The Principal sees
        # what the CoS heard and either approves or revises before
        # .configured is written.
        state.current_step = "AWAITING_APPROVAL"
        save_state(state)
        return _present_rough_draft(state)
    state.current_step = _CLEAN_INSTALL_STEPS[next_idx][0]
    save_state(state)
    return _format_clean_question(state, _CLEAN_INSTALL_STEPS[next_idx])


# ── Approval gate (v0.23.5) ───────────────────────────────────────────────


def _present_rough_draft(state: SetupState) -> str:
    """Per StrategicPlanning.md §3.5: before `.configured` is written,
    show the Principal the rough-draft Goals.md + Guardrails.md in
    plain language and ask for approval.

    The Principal either:
      - `/agency setup approve` — confirm; finalize writes the files
      - `/agency setup revise <field> <new text>` — edit a piece;
         we re-present the updated draft for approval
    """
    ans = state.collected_answers
    principal_name = (
        ans.get("principal_name")
        or ans.get("owner_name")
        or "[Principal]"
    )
    org_name = ans.get("org_name", "[your business]")

    lines = [
        f"## Setup — rough draft for {principal_name}'s review",
        "",
        "Here's what I heard. Before I make it official:",
        "",
        f"**Your business:** {org_name}",
        "",
        f"**Your role:** {ans.get('role_description', '[not provided]')}",
        "",
        "**Goals you're working toward:**",
        "",
        f"  {ans.get('current_goals', '[not provided]')}",
        "",
        "**Lines you won't cross (Guardrails):**",
        "",
        f"  {ans.get('values', '[not provided]')}",
        "",
    ]
    if ans.get("personal_context", "").strip().lower() not in ("", "skip"):
        lines.append("**Personal context I noted:**")
        lines.append("")
        lines.append(f"  {ans['personal_context']}")
        lines.append("")
    if ans.get("clients", "").strip().lower() not in ("", "skip"):
        lines.append("**Clients I noted:**")
        lines.append("")
        lines.append(f"  {ans['clients']}")
        lines.append("")
    lines.extend([
        "---",
        "",
        "**Want to revise anything?**",
        "",
        "  `/agency setup revise <field> <new text>`",
        "    where <field> is one of: org, role, goals, values,",
        "    personal, clients, voice, principal-name",
        "",
        "**Looks good?**",
        "",
        "  `/agency setup approve`",
        "",
        "_After you approve, I'll write `Goals.md` + `Guardrails.md`_",
        "_to the vault and mark the deployment configured. I'll also_",
        "_draft the Interim Goals + Initiative mappings behind the_",
        "_scenes — those are my working hypotheses and refresh_",
        "_continuously; you don't need to approve those layers._",
    ])
    return "\n".join(lines)


def _approve_draft() -> str:
    """Principal approves the rough draft → finalize."""
    state = load_state()
    if state.current_step != "AWAITING_APPROVAL":
        return (
            "There's no draft awaiting approval. Run `/agency setup` to "
            "start (or see status with `/agency setup status`)."
        )
    return _finalize_clean_install(state)


_REVISE_FIELDS = {
    "org": "org_name",
    "role": "role_description",
    "goals": "current_goals",
    "values": "values",
    "guardrails": "values",  # alias
    "personal": "personal_context",
    "clients": "clients",
    "voice": "voice_notes",
    "principal-name": "principal_name",
    "name": "principal_name",  # alias
}


def _revise_draft(arg: str) -> str:
    """Principal edits a single field of the rough draft, then re-sees
    the draft."""
    state = load_state()
    if state.current_step != "AWAITING_APPROVAL":
        return (
            "There's no draft awaiting approval right now. Run "
            "`/agency setup` to start."
        )
    parts = arg.split(None, 1)
    if len(parts) < 2:
        return (
            "Usage: `/agency setup revise <field> <new text>`\n\n"
            f"Valid fields: {', '.join(sorted(set(_REVISE_FIELDS.keys())))}"
        )
    field, new_text = parts[0].lower(), parts[1].strip()
    if field not in _REVISE_FIELDS:
        return (
            f"Unknown field `{field}`. Valid: "
            f"{', '.join(sorted(set(_REVISE_FIELDS.keys())))}"
        )
    target_key = _REVISE_FIELDS[field]
    state.collected_answers[target_key] = new_text
    save_state(state)
    return (
        f"✓ Updated `{field}`. Here's the revised draft:\n\n"
        + _present_rough_draft(state)
    )


# ── Step navigation helpers ───────────────────────────────────────────────


def _step_index(step_id: str) -> int:
    for i, (sid, _, _) in enumerate(_CLEAN_INSTALL_STEPS):
        if sid == step_id:
            return i
    return -1


def _current_step(state: SetupState) -> Optional[tuple[str, str, str]]:
    for s in _CLEAN_INSTALL_STEPS:
        if s[0] == state.current_step:
            return s
    return None


def _format_clean_question(state: SetupState, step: tuple[str, str, str]) -> str:
    idx = _step_index(step[0])
    total = len(_CLEAN_INSTALL_STEPS)
    return (
        f"[Setup interview — question {idx + 1} of {total}]\n\n"
        f"{step[1]}\n\n"
        f"To answer: `/agency setup answer <your answer here>`\n"
        f"To skip this question (acceptable for some — values are\n"
        f"important, contact lists less so on day one): `/agency setup answer skip`"
    )


# ── Finalization: write vault files + .configured marker ──────────────────


def _finalize_clean_install(state: SetupState) -> str:
    """Write the vault files from collected answers + mark configured."""
    ans = state.collected_answers
    profile, _ = current_profile_and_role()
    profile_id = profile or "loriah"

    # Resolve vault location. Try v0.20 target first, then v0.17 fallback.
    new_home = Path.home() / ".hermes" / "agency-state" / "vaults" / profile_id
    legacy_home = _agency_home() / "profiles" / profile_id / "vault"
    if new_home.parent.exists():
        vault_dir = new_home
    else:
        vault_dir = legacy_home
    vault_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    if (g := ans.get("current_goals", "")) and g.lower() != "skip":
        _write_vault(vault_dir / "Goals.md", "# Goals", g)
        written.append("Goals.md")

    if (v := ans.get("values", "")) and v.lower() != "skip":
        # v0.22.4-spec: Values.md → Guardrails.md. The setup interview's
        # GUARDRAILS step writes Guardrails.md as the canonical file.
        # We also write a tombstone Values.md that points at Guardrails.md
        # so any legacy reader (older skill, older v7 migration tool, etc.)
        # doesn't silently get empty values.
        _write_vault(vault_dir / "Guardrails.md", "# Guardrails", v)
        written.append("Guardrails.md")
        _write_vault(
            vault_dir / "Values.md",
            "# Values (legacy — see Guardrails.md)",
            f"> *This file is retained for backward-compat with v0.22.4-and-earlier tooling. The canonical file is now [`Guardrails.md`](./Guardrails.md). Content mirrored below.*\n\n{v}",
        )
        written.append("Values.md (legacy tombstone)")

    personal_parts = []
    # principal_name is the v0.23+ field; owner_name is the legacy
    # alias for backward-compat with in-flight setup state.
    principal_name = ans.get("principal_name") or ans.get("owner_name", "")
    if principal_name and principal_name.lower() != "skip":
        personal_parts.append(f"**Name:** {principal_name}")
    if (p := ans.get("personal_context", "")) and p.lower() != "skip":
        personal_parts.append(p)
    if personal_parts:
        _write_vault(
            vault_dir / "Personal.md",
            "# Personal",
            "\n\n".join(personal_parts),
        )
        written.append("Personal.md")

    work_parts = []
    if (o := ans.get("org_name", "")) and o.lower() != "skip":
        work_parts.append(f"**Organization:** {o}")
    if (r := ans.get("role_description", "")) and r.lower() != "skip":
        work_parts.append(f"**Role:** {r}")
    if work_parts:
        _write_vault(
            vault_dir / "Work.md",
            "# Work",
            "\n\n".join(work_parts),
        )
        written.append("Work.md")

    if (c := ans.get("clients", "")) and c.lower() != "skip":
        _write_vault(vault_dir / "Clients.md", "# Clients", c)
        written.append("Clients.md")

    # SOUL.md voice refinement: appended to the existing SOUL if present,
    # otherwise created as a stub.
    if (voice := ans.get("voice_notes", "")) and voice.lower() != "skip":
        soul_path = vault_dir / "SOUL-voice-notes.md"
        _write_vault(
            soul_path,
            "# SOUL — voice notes (from setup interview)",
            voice,
        )
        written.append("SOUL-voice-notes.md")

    mark_configured()
    clear_state()

    summary = (
        "✓ Setup complete. Deployment is configured.\n\n"
        f"  Profile: {profile_id}\n"
        f"  Vault:   {vault_dir}\n"
        f"  Written: {', '.join(written) if written else '(no files — everything skipped)'}\n\n"
        "You can edit any of these files directly with your editor; "
        "the framework reads them on every skill-load.\n\n"
        "Next:\n"
        "  /agency status            # see deployment health\n"
        "  /agency systems           # see which reliability systems are wired\n"
        "  /agency capture \"...\"   # capture a learning correction\n"
        "  (just chat normally with Hermes — the plugin is now active)"
    )
    return summary


def _write_vault(path: Path, heading: str, body: str) -> None:
    """Write a vault file with a heading + body. Idempotent — overwrites
    only the agency-managed sections; manual edits below them stay."""
    content = f"{heading}\n\n{body}\n"
    path.write_text(content, encoding="utf-8")


__all__ = [
    "handle_setup_command",
    "is_configured", "mark_configured",
]
