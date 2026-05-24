# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Tier 3 deep interview — generates first drafts of agency-level
context docs from a substantive interview with the principal.

The principal answers questions (about 30-45 min total). The
interview produces:

  agency-vault/Goals.md           — the single most important doc
  agency-vault/Values.md          — non-negotiables
  agency-vault/Personal.md        — non-work context
  agency-vault/Work.md            — what the agency offers
  agency-vault/Clients.md         — current roster
  profiles/<cos>/SOUL.md          — CoS's identity (refined)
  profiles/<cos>/standards.md     — CoS's quality floor (refined)

After generation, the principal edits freely. Re-running with
--refresh regenerates from a fresh interview, preserving the prior
version as `<file>.YYYY-MM-DD.bak`.

The interview is structured around sections (not a flat survey).
Each section gathers context for one doc + sets up the next
section's questions. Refusing/skipping a section leaves the
template placeholders intact for later manual editing.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from _framework.constants import (
    AGENCY_VAULT,
    CLIENTS_MD,
    GOALS_MD,
    PERSONAL_MD,
    STATE_VAULT,
    TEMPLATES_DIR,
    VALUES_MD,
    WORK_MD,
    profile_soul,
    profile_standards,
)


# ── Per-section question schemas ─────────────────────────────────────────


@dataclass
class Question:
    key: str             # the {{PLACEHOLDER}} to substitute
    prompt: str          # the human-readable question
    multiline: bool = False
    optional: bool = False
    follow_up: list[str] = field(default_factory=list)  # printed under the prompt


@dataclass
class Section:
    name: str
    doc_label: str       # e.g. "Goals.md" — shown to user
    intro: str           # printed before the section's questions
    questions: list[Question]
    template_relpath: str   # path under templates/agency-vault/ or templates/profiles/...
    output_path_resolver: Callable[[dict], Path]   # given gathered answers, return where to write
    extra_subs: dict[str, str] = field(default_factory=dict)


# Build the section list. Substantive questions — the goal is real
# content, not placeholder forms.

GOALS_SECTION = Section(
    name="goals",
    doc_label="Goals.md",
    intro=(
        "Goals.md is the single most important document the agency will read.\n"
        "Every prioritization decision routes back to it. We'll spend the\n"
        "longest here — about 10-15 minutes.\n"
    ),
    questions=[
        Question(
            key="MISSION_STATEMENT",
            prompt="In ONE paragraph: why does this agency exist? What outcome is the work in service of?",
            multiline=True,
            follow_up=[
                "Not the elevator pitch — the real reason. If everything goes",
                "well, what changes in the world?",
            ],
        ),
        Question(
            key="ANNUAL_GOALS",
            prompt="What 3-7 specific outcomes are you working toward in the next 12 months?",
            multiline=True,
            follow_up=[
                "Each one a measurable end state, not a process.",
                "Bad: 'grow the business.' Good: 'sign 4 new district clients by Q3.'",
            ],
        ),
        Question(
            key="ACTIVE_PROJECTS",
            prompt="What 2-5 named initiatives are getting most of your attention right now?",
            multiline=True,
            follow_up=[
                "For each: brief description, current phase, and who owns it day-to-day.",
            ],
        ),
        Question(
            key="EXPLICIT_NON_GOALS",
            prompt="What is your agency explicitly NOT working on, even though it might look adjacent?",
            multiline=True,
            follow_up=[
                "This list protects focus. Anything you've consciously",
                "decided is not your job — even when it looks like it could be.",
            ],
        ),
        Question(
            key="PROGRESS_METRICS",
            prompt="For each annual goal, what's the leading indicator that says it's on track?",
            multiline=True,
            optional=True,
            follow_up=[
                "Leading indicators, not lagging outcomes. What do you watch weekly?",
            ],
        ),
        Question(
            key="DECISION_PRINCIPLES",
            prompt="When two goals both want the next hour, how do you decide?",
            multiline=True,
            optional=True,
            follow_up=[
                "Document the actual rules of thumb you use. Agents apply them.",
            ],
        ),
    ],
    template_relpath="agency-vault/Goals.md.template",
    output_path_resolver=lambda _ans: GOALS_MD,
)

VALUES_SECTION = Section(
    name="values",
    doc_label="Values.md",
    intro=(
        "Values.md captures what you refuse to trade off, even under\n"
        "pressure. Agents read this to know which judgment calls are open\n"
        "and which are closed.\n"
    ),
    questions=[
        Question(
            key="CORE_VALUES",
            prompt="List 5-7 values you'd refuse to trade away even for big wins.",
            multiline=True,
            follow_up=[
                "Short phrases. 'Truth over comfort.' 'Family before work.'",
                "'Author's voice is sacred.' That kind of thing.",
            ],
        ),
        Question(
            key="WORK_QUALITY_STANDARDS",
            prompt="What does excellent work look like to you?",
            multiline=True,
            follow_up=[
                "The qualities you recognize as great work — in your own",
                "work and in others'. Agents calibrate against this.",
            ],
        ),
        Question(
            key="KEY_RELATIONSHIPS",
            prompt="Whose call always comes first?",
            multiline=True,
            follow_up=[
                "By category, not specific people. Family, key clients,",
                "long-time collaborators, etc.",
            ],
        ),
        Question(
            key="INTERPERSONAL_PRINCIPLES",
            prompt="How do you treat people you work with? Default style, escalation, disagreement.",
            multiline=True,
            follow_up=[
                "Agents speaking on your behalf calibrate against this.",
            ],
        ),
        Question(
            key="NON_NEGOTIABLES",
            prompt="What will you absolutely refuse to do, no matter the upside?",
            multiline=True,
            follow_up=[
                "Hard ceilings. Agents enforce these regardless of autonomy level.",
                "Example: 'Never send unrequested attachments.' 'Never quote",
                "internal financials externally.'",
            ],
        ),
        Question(
            key="CHALLENGE_PREFERENCES",
            prompt="How do you want to be challenged when an agent disagrees with you?",
            multiline=True,
            optional=True,
            follow_up=[
                "Adversarial review? Specific failure modes? Evidence first?",
                "Helps Analyst calibrate critique style.",
            ],
        ),
    ],
    template_relpath="agency-vault/Values.md.template",
    output_path_resolver=lambda _ans: VALUES_MD,
)

PERSONAL_SECTION = Section(
    name="personal",
    doc_label="Personal.md",
    intro=(
        "Personal.md is the non-work context the agency needs to be\n"
        "useful. Family, health, friends, commitments that shape the\n"
        "work without being the work. This is sensitive — only agents\n"
        "that need it will load it.\n"
        "\n"
        "You can skip any question by entering 'skip'. Skipped sections\n"
        "leave placeholders in the file for later editing.\n"
    ),
    questions=[
        Question(
            key="FAMILY_CONTEXT",
            prompt="Who's in your immediate family + any standing commitments tied to family time?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="HEALTH_CONTEXT",
            prompt="Sleep schedule, exercise, energy patterns, anything the agency should honor when scheduling?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="FRIENDS_COMMUNITY",
            prompt="Standing relationships outside work — friend groups, community, civic obligations?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="HOBBIES_RESTORATION",
            prompt="What do you do to restore? The agency protects this as fiercely as family time.",
            multiline=True,
            optional=True,
        ),
        Question(
            key="LIVING_CONTEXT",
            prompt="Home, location, travel patterns?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="PERSONAL_PROJECTS",
            prompt="Anything you're working on that isn't the agency's work but matters to you?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="WORK_LIFE_BOUNDARIES",
            prompt="Explicit boundaries: 'no work after 7pm', 'no work Sundays', etc.",
            multiline=True,
            follow_up=[
                "These become hard rules in CoS's scheduling logic.",
            ],
        ),
    ],
    template_relpath="agency-vault/Personal.md.template",
    output_path_resolver=lambda _ans: PERSONAL_MD,
)

WORK_SECTION = Section(
    name="work",
    doc_label="Work.md",
    intro=(
        "Work.md is the canonical 'what the work IS.' When someone asks\n"
        "what you do, the answer comes from here.\n"
    ),
    questions=[
        Question(
            key="AGENCY_OFFERINGS",
            prompt="What does the agency actually deliver? Specific.",
            multiline=True,
            follow_up=[
                "'We write code' is vague. 'We build internal data tools",
                "for K-12 districts' is right.",
            ],
        ),
        Question(
            key="ENGAGEMENT_MODEL",
            prompt="Shape of typical engagements: retainers? Projects? Hourly?",
            multiline=True,
        ),
        Question(
            key="ACTIVE_PROJECTS",
            prompt="Named active engagements right now. Client / brief / current phase / who's involved.",
            multiline=True,
            optional=True,
            follow_up=[
                "Updates as projects start and end; skip for the template if you'd rather edit by hand.",
            ],
        ),
        Question(
            key="REVENUE_STREAMS",
            prompt="Where's money coming from? By category, not finance-detailed.",
            multiline=True,
            optional=True,
        ),
        Question(
            key="STANDARD_RATES",
            prompt="Standard package + cost. Helps agents quote inbound inquiries without asking you each time.",
            multiline=True,
            optional=True,
        ),
        Question(
            key="TOOL_STACK",
            prompt="The actual stack the agency operates in. CRM, calendar, storage, billing, comms.",
            multiline=True,
        ),
        Question(
            key="WORK_LOCATIONS",
            prompt="Home office, co-working, client sites, travel?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="PROFESSIONAL_NETWORKS",
            prompt="Communities + associations + ongoing peer relationships you're embedded in?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="LEARNING_GROWTH",
            prompt="What are you currently learning or developing skill in?",
            multiline=True,
            optional=True,
        ),
    ],
    template_relpath="agency-vault/Work.md.template",
    output_path_resolver=lambda _ans: WORK_MD,
)

CLIENTS_SECTION = Section(
    name="clients",
    doc_label="Clients.md",
    intro=(
        "Clients.md is the relationship map. Sensitive content —\n"
        "pricing, embargo rules, client-specific quirks. Agents read it\n"
        "but never quote it outbound.\n"
    ),
    questions=[
        Question(
            key="ACTIVE_CLIENTS",
            prompt="Current active clients. Name / what we're doing / primary contact / expectations.",
            multiline=True,
        ),
        Question(
            key="COMPLETED_ENGAGEMENTS",
            prompt="Recently completed (last 6-12 months)?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="DORMANT_RELATIONSHIPS",
            prompt="Long-standing relationships not currently engaged — BD shouldn't prospect them as strangers.",
            multiline=True,
            optional=True,
        ),
        Question(
            key="COLLABORATORS",
            prompt="Standing collaborators — co-authors, sub-contractors, referral sources, peer firms.",
            multiline=True,
            optional=True,
        ),
        Question(
            key="CLIENT_COMM_PATTERNS",
            prompt="Per-client communication preferences? ('Acme wants weekly Friday updates.')",
            multiline=True,
            optional=True,
        ),
        Question(
            key="BILLING_CADENCE",
            prompt="When clients renew / when invoices go out / when retainers reset?",
            multiline=True,
            optional=True,
        ),
        Question(
            key="CLIENT_SPECIFIC_RULES",
            prompt="Any client-specific hard rules? Exclusivity, embargoes, no-fly recipients?",
            multiline=True,
            optional=True,
            follow_up=[
                "Agents enforce these at the send-guard layer.",
            ],
        ),
    ],
    template_relpath="agency-vault/Clients.md.template",
    output_path_resolver=lambda _ans: CLIENTS_MD,
)


SECTIONS: list[Section] = [
    GOALS_SECTION,
    VALUES_SECTION,
    PERSONAL_SECTION,
    WORK_SECTION,
    CLIENTS_SECTION,
]


# ── Interview runner ─────────────────────────────────────────────────────


def run_tier3_interview(
    owner_name: str,
    org_name: str,
    cos_id: str | None = None,
    prompter: Callable[[Question], str] | None = None,
    refresh: bool = False,
    profiles_to_personalize: list[tuple[str, str]] | None = None,
    persona_prompter: Callable[[str, str, str], str] | None = None,
) -> dict[str, Path]:
    """Run the deep interview. Returns {section_name: output_path} for
    each generated doc. Prompter abstraction makes this testable.

    `profiles_to_personalize`: iter of (profile_id, role) for the
    per-agent personalization section. When None, that section is
    skipped (Tier 1 callers don't pass this; full Tier 3 does).
    """

    prompter = prompter or _interactive_prompter
    AGENCY_VAULT.mkdir(parents=True, exist_ok=True)
    STATE_VAULT.mkdir(parents=True, exist_ok=True)

    interview_date = datetime.now().strftime("%Y-%m-%d")
    common_subs = {
        "OWNER_NAME": owner_name or "{{OWNER_NAME}}",
        "ORG_NAME": org_name or "{{ORG_NAME}}",
        "INTERVIEW_DATE": interview_date,
    }

    print()
    print("=" * 70)
    print("  Tier 3 — Deep Interview")
    print("=" * 70)
    print(
        f"""
About 30-45 minutes. We'll work through five sections — one per
agency-vault doc. You can skip any optional question with 'skip',
or end the interview at any time with Ctrl-C (work so far gets
saved).

Multi-line answers: end with a line containing just '.' to submit.

The five sections:
  1. Goals.md         — what we're optimizing for
  2. Values.md        — what we refuse to trade off
  3. Personal.md      — non-work context (sensitive)
  4. Work.md          — what the agency offers
  5. Clients.md       — current roster (sensitive)
"""
    )

    generated: dict[str, Path] = {}

    for section in SECTIONS:
        print()
        print("─" * 70)
        print(f"  Section: {section.doc_label}")
        print("─" * 70)
        print(section.intro)

        answers: dict[str, str] = {}
        skipped = 0
        for q in section.questions:
            answer = prompter(q)
            if answer in ("skip", "", None) and q.optional:
                # leave placeholder
                skipped += 1
                continue
            answers[q.key] = answer.strip() if answer else ""

        # Render template with answers
        output_path = section.output_path_resolver(answers)
        if output_path.exists() and not refresh:
            print(f"  ! {output_path.name} exists; skipping (pass --refresh to regenerate)")
            continue

        if output_path.exists() and refresh:
            backup = output_path.with_suffix(f".{interview_date}.bak")
            shutil.copy2(output_path, backup)
            print(f"  ✓ backed up prior {output_path.name} → {backup.name}")

        template_text = (TEMPLATES_DIR / section.template_relpath).read_text(encoding="utf-8")
        rendered = _render(template_text, {**common_subs, **answers, **section.extra_subs})
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        generated[section.name] = output_path
        print(f"  ✓ wrote {output_path}")
        if skipped:
            print(f"    ({skipped} optional question(s) skipped — placeholders remain for later editing)")

    # ── Per-agent personalization ──────────────────────────────────────
    if profiles_to_personalize:
        from .agent_personalization import (
            personalize_agents, write_persona_appendices,
        )
        personas = personalize_agents(
            profiles=profiles_to_personalize,
            prompter=persona_prompter,
        )
        written = write_persona_appendices(personas, interview_date)
        for pid in written:
            generated[f"persona:{pid}"] = profile_soul(pid)
            print(f"  ✓ appended personalization to profile {pid}'s SOUL.md")

    # ── CoS voice notes (focused detail beyond the per-agent step) ─────
    if cos_id:
        print()
        print("─" * 70)
        print(f"  Section: ChiefOfStaff voice ({cos_id})")
        print("─" * 70)
        print(
            "One more focused question for CoS specifically — she carries\n"
            "the agency's outbound voice. The per-agent personalization\n"
            "above captured tone; this captures voice specifics.\n"
        )
        cos_q = Question(
            key="COS_VOICE_NOTES",
            prompt="Specific voice notes for outbound? (we-not-I, warm without flattering, etc.)",
            multiline=True,
            optional=True,
            follow_up=[
                "These get appended to CoS's SOUL.md as voice rules.",
                "Skip if the per-agent personality already covered it.",
            ],
        )
        voice = prompter(cos_q)
        if voice and voice != "skip":
            soul = profile_soul(cos_id)
            if soul.exists():
                addendum = (
                    f"\n\n## Voice notes (from Tier 3 interview {interview_date})\n\n"
                    f"{voice}\n"
                )
                soul.write_text(soul.read_text(encoding="utf-8") + addendum, encoding="utf-8")
                print(f"  ✓ appended voice notes to {soul}")
                generated["cos_voice"] = soul

    # ── State-vault stubs ───────────────────────────────────────────────
    from . import _state_files
    _state_files.ensure_initial_state_files(owner_name=owner_name, interview_date=interview_date)

    print()
    print("=" * 70)
    print(f"  Tier 3 interview complete. Generated {len(generated)} doc(s).")
    print("=" * 70)
    print(f"\n  See: {AGENCY_VAULT}")
    print(f"  Read: {AGENCY_VAULT}/README.md\n")
    return generated


# ── Prompter ─────────────────────────────────────────────────────────────


def _interactive_prompter(q: Question) -> str:
    """Interactive stdin/stdout prompter. Multi-line answers end with '.' alone."""
    print()
    print(f"  Q: {q.prompt}")
    for line in q.follow_up:
        print(f"     {line}")
    if q.optional:
        print("     (optional — type 'skip' to leave a placeholder)")
    if q.multiline:
        print("     (multi-line: end with a line containing just '.')")
        lines = []
        try:
            while True:
                line = input("     > ")
                if line.strip() == ".":
                    break
                if line.strip() == "skip" and not lines:
                    return "skip"
                lines.append(line)
        except EOFError:
            pass
        return "\n".join(lines)
    try:
        ans = input("     > ").strip()
    except EOFError:
        ans = ""
    return ans


def _render(template: str, subs: dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders. Missing keys are left intact for
    later manual filling (so skipped questions don't break the doc)."""
    out = template
    for k, v in subs.items():
        if v:
            out = out.replace(f"{{{{{k}}}}}", v)
    return out


__all__ = ["run_tier3_interview", "Section", "Question", "SECTIONS"]
