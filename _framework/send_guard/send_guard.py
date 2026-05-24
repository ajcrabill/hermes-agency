# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
send_guard — the canonical outbound-mail validator.

Public function: `evaluate(message: SendCandidate) -> SendGuardDecision`.

A `SendCandidate` carries: to/cc/bcc, from_addr, subject, body, skill,
profile, intended_action_class. The guard returns:

  - ALLOW    proceed to send
  - HOLD     queue for owner review (greylist + autonomy class
             requires human confirmation)
  - DENY     refuse (blacklist, hard ceiling, hard-rule violation)

Every DENY records firings for the violated hard rules so the
learning subsystem sees the override attempts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from _framework.manifest import load_invariants
from _framework.constants import AGENCY_HOME


class Verdict(Enum):
    ALLOW = "allow"
    HOLD = "hold"
    DENY = "deny"


@dataclass
class SendCandidate:
    to: list[str]
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    from_addr: str = ""
    subject: str = ""
    body: str = ""
    skill: str = ""
    profile: str = ""
    intended_action_class: str = "send-single"
    is_first_message: bool = False


@dataclass
class SendGuardDecision:
    verdict: Verdict
    reasons: list[str] = field(default_factory=list)
    firings: list[dict] = field(default_factory=list)   # {rule_id, skill, profile, was_overridden, summary}

    @property
    def allowed(self) -> bool:
        return self.verdict == Verdict.ALLOW

    def render(self) -> str:
        lines = [f"verdict: {self.verdict.value}"]
        for r in self.reasons:
            lines.append(f"  - {r}")
        return "\n".join(lines)


# ── Access list (three-tier) ────────────────────────────────────────────


@dataclass
class AccessList:
    """Loaded from email-access.md. Each section is a list of email addresses,
    one per line, with optional comments after `#`."""

    whitelist: set[str] = field(default_factory=set)
    greylist:  set[str] = field(default_factory=set)
    blacklist: set[str] = field(default_factory=set)


def load_access_list(path: Path | str | None = None) -> AccessList:
    """Parse the operator-edited markdown access list."""
    if path is None:
        # Best-effort default: look in the CoS profile's scripts dir if
        # discoverable, else return empty lists.
        return AccessList()
    p = Path(str(path)).expanduser()
    if not p.exists():
        return AccessList()

    al = AccessList()
    current: set[str] | None = None
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("# whitelist") or lower.startswith("## whitelist"):
            current = al.whitelist
            continue
        if lower.startswith("# greylist") or lower.startswith("## greylist"):
            current = al.greylist
            continue
        if lower.startswith("# blacklist") or lower.startswith("## blacklist"):
            current = al.blacklist
            continue
        if line.startswith("#"):
            current = None
            continue
        if current is None:
            continue
        # Strip inline comments
        token = line.split("#", 1)[0].strip().lstrip("-*").strip()
        if "@" in token:
            current.add(token.lower())
    return al


# ── Hard-rule registry (deterministic validators) ────────────────────────


HARD_RULE_VALIDATORS: dict[str, "callable"] = {}  # type: ignore[type-arg]


def register_hard_validator(rule_id: str):
    """Decorator to register a function `fn(candidate) -> (passed, message)`
    that enforces a specific hard rule by id."""

    def deco(fn):
        HARD_RULE_VALIDATORS[rule_id] = fn
        return fn

    return deco


# Example built-in validators. Deployments add their own by:
#   (a) capturing a hard rule (is_hard=1)
#   (b) declaring a validator in their CoS profile's send-guard config
# The framework only ships generic ones.


@register_hard_validator("no-domain-blacklist")
def _no_blacklist_domain(candidate: SendCandidate, access: AccessList) -> tuple[bool, str]:
    """Generic check — any recipient on the blacklist denies."""
    recips = set(candidate.to) | set(candidate.cc) | set(candidate.bcc)
    bad = [r for r in recips if r.lower() in access.blacklist]
    if bad:
        return False, f"blacklisted recipient(s): {bad}"
    return True, "no blacklisted recipients"


# NOTE: first-message-to-new-contact is enforced as a HARD CEILING (§4.5)
# in the evaluate() function below — it produces a HOLD verdict, not a
# DENY. Registering a hard-rule validator for it would turn HOLD into
# DENY, which is the wrong shape for that ceiling.


# ── Evaluate ─────────────────────────────────────────────────────────────


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def evaluate(
    candidate: SendCandidate,
    access_list: AccessList | None = None,
) -> SendGuardDecision:
    """Run the candidate through the four layers. First DENY wins; else
    if any HOLD signals, return HOLD; else ALLOW.

    Layer order:
        L1 access list (whitelist / greylist / blacklist)
        L2 hard ceilings (manifest invariants)
        L3 hard-rule validators (registered validators)
        L4 Guardrails.md awareness (v0.23+)

    L4 loads Guardrails.md and notes its presence in the decision
    record so the audit / Sentinel can verify the send-guard
    actually saw the Principal's declared lines. The semantic
    check against Guardrail content (does this message look like
    it would violate a prohibition?) is LLM-driven and ships in
    a follow-up release; for now the integration is structural.
    """
    decision = SendGuardDecision(verdict=Verdict.ALLOW)

    if access_list is None:
        access_list = AccessList()

    # ── shape checks (obvious malformed input) ──────────────────────────
    if not candidate.to:
        decision.verdict = Verdict.DENY
        decision.reasons.append("no recipients")
        return decision
    for addr in [*candidate.to, *candidate.cc, *candidate.bcc]:
        if not _EMAIL_RE.match(addr):
            decision.verdict = Verdict.DENY
            decision.reasons.append(f"malformed address: {addr}")
            return decision

    # ── Layer 1: access list ────────────────────────────────────────────
    recips = set(candidate.to) | set(candidate.cc) | set(candidate.bcc)
    bad = [r for r in recips if r.lower() in access_list.blacklist]
    if bad:
        decision.verdict = Verdict.DENY
        decision.reasons.append(f"blacklisted recipient(s): {bad}")
        decision.firings.append({
            "rule_id": "send-guard-blacklist",
            "skill": candidate.skill,
            "profile": candidate.profile,
            "was_overridden": True,
            "summary": f"attempted send to blacklist {bad}",
        })
        return decision

    grey = [r for r in recips if r.lower() in access_list.greylist]

    # ── Layer 2: hard ceilings ──────────────────────────────────────────
    inv = load_invariants()
    ceilings = set(inv.get("hard_send_ceilings", []))
    if candidate.is_first_message and "new-contact-first-message" in ceilings:
        decision.verdict = Verdict.HOLD
        decision.reasons.append("first-message-to-new-contact: holding for owner approval (hard ceiling)")

    # ── Layer 3: hard-rule validators ──────────────────────────────────
    for rule_id, fn in HARD_RULE_VALIDATORS.items():
        try:
            passed, msg = fn(candidate, access_list)
        except TypeError:
            # validator without access_list arg
            passed, msg = fn(candidate)  # type: ignore[misc]
        except Exception as e:  # pragma: no cover
            passed, msg = False, f"validator '{rule_id}' raised: {e}"
        if not passed:
            decision.verdict = Verdict.DENY
            decision.reasons.append(f"hard-rule {rule_id}: {msg}")
            decision.firings.append({
                "rule_id": rule_id,
                "skill": candidate.skill,
                "profile": candidate.profile,
                "was_overridden": True,
                "summary": msg,
            })

    if decision.verdict == Verdict.DENY:
        return decision

    if grey and decision.verdict != Verdict.HOLD:
        decision.verdict = Verdict.HOLD
        decision.reasons.append(f"greylist recipient(s): {grey} — holding for Principal review")

    # ── Layer 4: Interim Guardrails awareness (v0.23+) ─────────────────
    # Per v0.22.4-spec aim/brake split, send-guard reads Guardrails.md
    # at outbound-mail pre_tool_call time. Guardrails themselves are
    # value statements (not SMART, not measurable); the SMART layer
    # is the Interim Guardrails underneath. Semantic checking (does
    # this message body advance / threaten a specific Interim Guardrail
    # metric?) is LLM-driven and ships in a follow-up release; for
    # now we load the structure and record that the send-guard saw it,
    # so the audit can verify the integration is wired correctly.
    try:
        from _framework.guardrails_loader import load_guardrails_parsed
        parsed = load_guardrails_parsed()
        if parsed:
            interim_count = sum(
                len(g.get("interim_guardrails", []))
                for g in parsed.get("guardrails", [])
            )
            decision.reasons.append(
                f"guardrails-loaded: {interim_count} Interim Guardrail(s) "
                f"in scope under {len(parsed.get('guardrails', []))} "
                f"Guardrail(s) (structural check only — semantic v0.23+)"
            )
    except ImportError:
        pass  # loader unavailable; not a send-guard failure

    if decision.verdict == Verdict.ALLOW:
        decision.reasons.append("clean")
    return decision


__all__ = [
    "Verdict",
    "SendCandidate",
    "SendGuardDecision",
    "AccessList",
    "load_access_list",
    "register_hard_validator",
    "HARD_RULE_VALIDATORS",
    "evaluate",
]
