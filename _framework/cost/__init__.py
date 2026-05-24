# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Per-skill cost + token attribution.

Every inference call records its tokens-in / tokens-out / cost
against the calling skill. The framework rolls up per skill, role,
day, week — surfaced in the compliance report + a `agency cost`
CLI surface. Operators can set per-skill budgets that block at L4+
when exceeded.

The framework is vendor-neutral, so the cost calculation is too —
each provider has its own pricing. Operators register cost
calculators per (provider, model); the framework calls them.

Schema:
  inference_calls  one row per inference call
  cost_budgets     operator-defined per-skill (or per-role) budgets
"""

from .cost_db import (
    init_cost_db,
    record_inference_call,
    list_inference_calls,
    skill_totals,
    role_totals,
    daily_totals,
    set_budget,
    get_budget,
    check_budget,
    InferenceCall,
    BudgetVerdict,
)
from .pricing import register_pricer, compute_cost_cents

__all__ = [
    "init_cost_db",
    "record_inference_call",
    "list_inference_calls",
    "skill_totals", "role_totals", "daily_totals",
    "set_budget", "get_budget", "check_budget",
    "InferenceCall", "BudgetVerdict",
    "register_pricer", "compute_cost_cents",
]
