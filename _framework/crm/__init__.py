# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
CRM module — contacts, leads, sent_threads, reply_log.

Generic substrate for any deployment's business-development +
inbound-routing needs. BD uses it for pipeline tracking; CoS's
`owner-channels-ingress` uses it for reply-to-thread matching.

Four-priority reply matching (matches v7's pattern):
  1. thread_id  — Gmail/IMAP thread id → sent_thread → lead
  2. email      — sender email → contacts.email or alternate_emails
  3. domain     — sender domain → leads with same domain
  4. unmatched  — caller flags for owner review

The CRM DB lives at `<AGENCY_HOME>/_state/crm.db` by default;
deployments can override per-profile (a BD profile that wants its
own DB sets `crm_db_path` in `profile.config.yaml`).
"""

from .crm_db import (
    init_crm_db,
    add_contact,
    update_contact,
    find_contact,
    find_contact_by_email,
    add_lead,
    update_lead,
    list_leads,
    find_lead_by_domain,
    log_sent_thread,
    find_sent_thread,
    log_reply,
    find_recent_replies,
)
from .reply_matcher import match_reply, ReplyMatch

__all__ = [
    "init_crm_db",
    "add_contact", "update_contact", "find_contact", "find_contact_by_email",
    "add_lead", "update_lead", "list_leads", "find_lead_by_domain",
    "log_sent_thread", "find_sent_thread",
    "log_reply", "find_recent_replies",
    "match_reply", "ReplyMatch",
]
