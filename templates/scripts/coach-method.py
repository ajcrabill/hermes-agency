#!/usr/bin/env python3
# FRAMEWORK-PROVIDED STARTER.
"""
coach-method — the self-contained coaching cron.

⚠ ARCHITECTURE RULE: this is a no_agent cron. The script handles
all decisions; the inference API is called as a TOOL (for question
generation + response classification) only. No LLM agent has
write access to coaching.db or mail.

Why: v7's prior architecture handed decisions to an LLM cron agent
that had DB write access. The LLM became "creative" — deleted
history, generated wrong batch numbers, sent unauthorized emails.
The no_agent design eliminates that failure mode by separating
deterministic flow control from inference-as-content-generation.

Cron cadence: every 60 minutes (no_agent=true in jobs.json)

This script is a starter shape. Operator customizes:
  - METHODOLOGY (which phase names, question templates, depth rules)
  - INFERENCE_CLIENT (which provider — DeepSeek, OpenAI-compat,
    local Ollama, etc.)
  - MAIL_TRANSPORT (Himalaya CLI, Gmail OAuth, IMAP)
"""

from __future__ import annotations

import argparse
import sys

from _framework.coaching import (
    list_active_projects, get_open_questions,
    record_qa, answer_question,
    find_user_by_email,
)
from _framework.heartbeats import beat
from _framework.learning import record_firing
from _framework.sentinel import append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coaching cycle (no_agent)")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    actions = {"questions_sent": 0, "answers_recorded": 0, "errors": 0}

    try:
        projects = list_active_projects()
    except Exception as e:
        append_event("coach_method_failed", actor=args.profile,
                     severity="critical", payload={"error": str(e)})
        beat(f"{args.profile}-coach-method")
        return 1

    for project in projects:
        try:
            # ── 1. Check for new inbound (the MAIL_TRANSPORT block) ──
            # Replace this stub with your transport's "list new messages
            # matching subject 'coach-<short-name>' or threaded to a
            # prior question" implementation.
            #
            # for msg in mail.list_new_to(project["short_name"]):
            #     answer_text = parse_answer(msg)
            #     source = "voice" if msg.has_audio else "typed"
            #     open_qs = get_open_questions(project["id"])
            #     matched_q = match_question(answer_text, open_qs)
            #     if matched_q:
            #         answer_question(matched_q["id"], answer_text,
            #                          answer_source=source)
            #         actions["answers_recorded"] += 1
            pass

            # ── 2. If no open questions in current phase, generate new batch ──
            open_qs = get_open_questions(project["id"], phase_number=project["phase"])
            if not open_qs:
                # ── Generate questions (the INFERENCE_CLIENT block) ──
                # Call your inference API as a tool to draft N questions.
                # The script holds the DB write authority; the LLM is
                # only generating content.
                #
                # questions = inference_client.generate_questions(
                #     methodology=project["methodology"],
                #     phase=project["phase"],
                #     prior_qa=get_qa_history(project["id"], phase_number=project["phase"]),
                #     count=project["questions_per_cycle"],
                #     depth=project["question_depth"],
                # )
                # for q_text in questions:
                #     record_qa(
                #         project_id=project["id"],
                #         phase_number=project["phase"],
                #         question=q_text,
                #         question_cycle=...,
                #     )
                # actions["questions_sent"] += len(questions)
                #
                # mail.send(
                #     to=find_user(project["user_id"])["email"],
                #     subject=f"coach-{project['short_name']}",
                #     body=render_question_batch(questions),
                # )
                pass

        except Exception as e:
            actions["errors"] += 1
            append_event(
                "coach_method_project_failed",
                actor=args.profile, target=str(project["id"]),
                severity="warn",
                payload={"project_id": project["id"], "error": str(e)},
            )

    severity = "warn" if actions["errors"] else "info"
    append_event(
        "coach_method_ran", actor=args.profile, severity=severity,
        payload={
            "projects_processed": len(projects),
            **actions,
        },
    )
    beat(f"{args.profile}-coach-method")
    return 0 if actions["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
