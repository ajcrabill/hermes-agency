# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Send-guard — outbound mail validation. The last gate before send.

Composes three lines of defense:

  1. ACCESS LIST     three-tier whitelist/greylist/blacklist
                     (`email-access.md` is the operator-edited source)
  2. HARD CEILINGS   actions that are never autonomous regardless of
                     skill level (per `invariants.yaml::hard_send_ceilings`)
  3. HARD RULES      learned `is_hard=1` rules with deterministic
                     validators (e.g. "never CC the board") — declared
                     in `send-guard-rules.yaml`, validated by registered
                     functions

Returns a SendGuardDecision: { allowed, reasons[], firings[] }.
Hard-rule violations are recorded as firings with `was_overridden=1`
so the loop can detect attempted breaches.
"""

from .send_guard import (
    AccessList,
    SendCandidate,
    SendGuardDecision,
    Verdict,
    evaluate,
    load_access_list,
    register_hard_validator,
)

__all__ = [
    "AccessList",
    "SendCandidate",
    "SendGuardDecision",
    "Verdict",
    "evaluate",
    "load_access_list",
    "register_hard_validator",
]
