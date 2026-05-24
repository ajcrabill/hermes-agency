# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Autonomy subsystem — the L1-L5 ladder.

Skills earn autonomy. Every skill starts at L1 (draft-only) and is
promoted L→L+1 only when *all three* inputs hold (§4.3 of spec):

  1. TRACK RECORD       — N consecutive clean_run events
  2. STRUCTURAL COMPLY  — audit-alignment.py --strict returns 0
  3. LEARNING FIDELITY  — no recapture events implicating skill,
                          and if rules >3 then >0 firings in 30d

Any single failure on any input demotes (or refuses promotion).

The graduation gate (`graduation_audit_gate`) is the audit-side check
hooked at the promotion-decision point inside `cmd_record_event`.

Action gate (`autonomy_gate.sh`) is the runtime check before any
consequential action: does the skill have authority for this action
class at its current level?
"""

from .autonomy_db import (
    init_autonomy_db,
    get_skill_level,
    set_skill_level,
    get_action_class_min_level,
)
from .autonomy_engine import (
    record_event,
    promote,
    demote,
    Promotion,
    Demotion,
)
from .graduation_audit_gate import graduation_audit_gate, AuditGateResult

__all__ = [
    "init_autonomy_db",
    "get_skill_level",
    "set_skill_level",
    "get_action_class_min_level",
    "record_event",
    "promote",
    "demote",
    "Promotion",
    "Demotion",
    "graduation_audit_gate",
    "AuditGateResult",
]
