# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Agency-level context-document loader.

Per spec §1.1, HermesAgency's agency-level context docs — Goals.md,
Personal.md, Work.md, Clients.md, and per-profile SOUL.md — are
always part of the operating background. Skills see them every turn,
alongside the injected learning rules.

`Guardrails.md` is intentionally NOT in this module's output. Per the
v0.22.4-spec aim-vs-brake split, Guardrails are loaded by the
enforcement layer (Sentinel, send-guard, audit) — not by the
always-on prompt context. See `_framework.guardrails_loader` for the
enforcement-layer reader.

Public API:
    load_agency_context(profile: str) -> str
        Returns a markdown block to prepend to the prompt at
        pre_llm_call. Empty string if no docs are present (which
        is a configuration anomaly the audit's
        `agency-context-injection` rule flags).
"""

from .loader import load_agency_context

__all__ = ["load_agency_context"]
