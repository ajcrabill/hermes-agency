# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Reply matcher — the 4-priority pattern from v7.

Given an inbound message (from email + Gmail thread id), match it
to a CRM lead. Priority order:

  1. Thread id    — sent_threads.thread_id → lead
  2. Email match  — contacts.email or contacts.alternate_emails → lead
  3. Domain match — leads tied to the sender's email domain
  4. Unmatched   — caller flags for owner review

The pattern catches replies from ANY address that comes through a
thread we sent (priority 1), then from anyone in our CRM at all
(priority 2), then from anyone whose org we have a lead with
(priority 3), then surfaces the rest.

Used by BD's `crm-sync` and CoS's `owner-channels-ingress`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .crm_db import (
    find_contact_by_email,
    find_lead_by_domain,
    find_sent_thread,
)


@dataclass
class ReplyMatch:
    """Result of matching an inbound reply against the CRM."""

    priority: int          # 1-4
    matched: bool          # True if priority 1-3, False if 4 (unmatched)
    lead_id: int | None = None
    contact_id: int | None = None
    thread_id: str | None = None
    domain_candidates: list[dict] | None = None  # populated only when priority=3
    reason: str = ""


def match_reply(
    *,
    from_email: str,
    thread_id: str | None = None,
    db_path: Path | None = None,
) -> ReplyMatch:
    """Run the 4-priority match. Returns a ReplyMatch with the verdict."""
    if not from_email:
        return ReplyMatch(priority=4, matched=False, reason="no from_email")

    # ── Priority 1: thread_id ──────────────────────────────────────────
    if thread_id:
        sent = find_sent_thread(thread_id, db_path=db_path)
        if sent:
            return ReplyMatch(
                priority=1,
                matched=True,
                lead_id=sent.get("lead_id"),
                contact_id=sent.get("contact_id"),
                thread_id=thread_id,
                reason=f"thread_id match → lead {sent.get('lead_id')}",
            )

    # ── Priority 2: email match (primary + alternates) ─────────────────
    contact = find_contact_by_email(from_email, db_path=db_path)
    if contact:
        return ReplyMatch(
            priority=2,
            matched=True,
            lead_id=contact.get("lead_id"),
            contact_id=contact.get("id"),
            thread_id=thread_id,
            reason=f"email match → contact {contact.get('id')} (lead {contact.get('lead_id')})",
        )

    # ── Priority 3: domain match ───────────────────────────────────────
    domain_candidates = find_lead_by_domain(from_email, db_path=db_path)
    if domain_candidates:
        # If exactly one domain candidate, attribute confidently.
        if len(domain_candidates) == 1:
            return ReplyMatch(
                priority=3,
                matched=True,
                lead_id=domain_candidates[0].get("id"),
                thread_id=thread_id,
                domain_candidates=domain_candidates,
                reason=f"domain match → lead {domain_candidates[0].get('id')} "
                       f"(unique candidate)",
            )
        # Multiple candidates — surface them but don't auto-attribute.
        return ReplyMatch(
            priority=3,
            matched=True,
            lead_id=None,        # caller decides among candidates
            thread_id=thread_id,
            domain_candidates=domain_candidates,
            reason=f"domain match → {len(domain_candidates)} candidates "
                   "(ambiguous; needs owner triage)",
        )

    # ── Priority 4: unmatched ──────────────────────────────────────────
    return ReplyMatch(
        priority=4,
        matched=False,
        thread_id=thread_id,
        reason="no thread, email, or domain match",
    )


__all__ = ["ReplyMatch", "match_reply"]
