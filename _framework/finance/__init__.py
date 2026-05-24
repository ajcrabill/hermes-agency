# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Finance subsystem — invoices, expenses, revenue, budget, vendor
payments.

The framework provides the substrate: schema, CRUD, categorization
helpers, cash-flow + burn-rate computation, revenue attribution.
The *policy* (which categories your agency uses, payment terms with
specific vendors, budget thresholds) lives in your deployment.

Schema (`_framework/finance/finance_db.py::finance.db`):
  invoices_in    — bills from vendors
  invoices_out   — bills you sent clients
  expenses       — non-invoice spending (subscriptions, ad-hoc)
  revenue        — money received, with attribution
  vendor_payments  — outbound payments (linked to invoices_in)
  budget_lines   — operator-defined budget per category per period

Public API surfaces enough for the 7 skills (cash-flow-tracker,
burn-rate-monitor, invoice-management, revenue-attribution,
expense-categorizer, budget-vs-actual, quarterly-financial-summary)
to operate.

The framework deliberately does NOT ship a default category list.
That's an operator decision (every agency's chart of accounts is
different). The wizard's Tier 3 deep-interview asks for it; until
then, "uncategorized" is the placeholder.
"""

from .finance_db import (
    init_finance_db,
    # invoices in
    add_invoice_in, list_invoices_in, mark_invoice_in_paid,
    overdue_invoices_in,
    # invoices out
    add_invoice_out, list_invoices_out, mark_invoice_out_paid,
    overdue_invoices_out,
    # expenses
    add_expense, list_expenses, categorize_expense,
    # revenue
    add_revenue, list_revenue, revenue_by_source,
    # budget
    set_budget_line, get_budget_line, list_budget_lines,
)
from .computations import (
    cash_position, monthly_burn, runway_months,
    revenue_attribution_summary,
    budget_vs_actual,
)

__all__ = [
    "init_finance_db",
    "add_invoice_in", "list_invoices_in", "mark_invoice_in_paid",
    "overdue_invoices_in",
    "add_invoice_out", "list_invoices_out", "mark_invoice_out_paid",
    "overdue_invoices_out",
    "add_expense", "list_expenses", "categorize_expense",
    "add_revenue", "list_revenue", "revenue_by_source",
    "set_budget_line", "get_budget_line", "list_budget_lines",
    "cash_position", "monthly_burn", "runway_months",
    "revenue_attribution_summary", "budget_vs_actual",
]
