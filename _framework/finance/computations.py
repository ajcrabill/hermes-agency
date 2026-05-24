# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Derived finance computations: cash position, burn rate, runway,
revenue attribution, budget vs actual.

These are pure read functions over `finance.db`. They produce
dicts the finance skills render into reports.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .finance_db import (
    list_expenses, list_revenue, list_invoices_in, list_invoices_out,
    list_budget_lines, revenue_by_source,
)


def cash_position(
    *, opening_cents: int = 0, since: str | None = None,
    db_path: Path | None = None,
) -> dict:
    """Current cash position = opening + revenue - expenses - vendor_payments.

    Operator passes `opening_cents` (typically the bank balance at the
    start of the period). The framework can't know your bank balance —
    operator wires this in.
    """
    revenue_total = sum(r["amount_cents"] for r in list_revenue(since=since, db_path=db_path))
    expense_total = sum(e["amount_cents"] for e in list_expenses(since=since, db_path=db_path))
    return {
        "opening_cents": opening_cents,
        "revenue_cents": revenue_total,
        "expense_cents": expense_total,
        "position_cents": opening_cents + revenue_total - expense_total,
    }


def monthly_burn(*, months: int = 3, db_path: Path | None = None) -> dict:
    """Rolling N-month average burn (expenses + paid vendor invoices).

    Returns: {'months_window': N, 'total_cents': X,
              'monthly_avg_cents': Y, 'detail': [...]}.
    """
    months = max(1, months)
    now = datetime.now(timezone.utc)
    since_dt = now - timedelta(days=30 * months)
    since = since_dt.isoformat()
    expenses = list_expenses(since=since, db_path=db_path)
    total = sum(e["amount_cents"] for e in expenses)
    avg = total / months if months else 0
    return {
        "months_window": months,
        "since": since,
        "total_cents": total,
        "monthly_avg_cents": int(avg),
        "expense_count": len(expenses),
    }


def runway_months(
    *, cash_position_cents: int, burn_window_months: int = 3,
    db_path: Path | None = None,
) -> dict:
    """Months of runway at the current burn rate.

    Operator-provided cash_position_cents (the framework doesn't
    know the bank balance — pass `cash_position()` output here or
    a manual value).
    """
    burn = monthly_burn(months=burn_window_months, db_path=db_path)
    monthly = burn["monthly_avg_cents"]
    if monthly <= 0:
        return {
            "months_remaining": float("inf"),
            "burn_used_monthly_cents": monthly,
            "cash_position_cents": cash_position_cents,
            "note": "no expenses recorded in window — runway undefined",
        }
    months = cash_position_cents / monthly
    return {
        "months_remaining": round(months, 2),
        "burn_used_monthly_cents": monthly,
        "cash_position_cents": cash_position_cents,
        "burn_window_months": burn_window_months,
    }


def revenue_attribution_summary(
    *, since: str | None = None, db_path: Path | None = None,
) -> dict:
    """% of revenue per source. Useful for "what's actually working?"."""
    rows = revenue_by_source(since=since, db_path=db_path)
    total = sum(r["total_cents"] for r in rows)
    enriched = []
    for r in rows:
        pct = (r["total_cents"] / total * 100) if total else 0.0
        enriched.append({
            **r,
            "pct_of_total": round(pct, 1),
        })
    return {
        "total_cents": total,
        "by_source": enriched,
    }


def budget_vs_actual(
    *, period_start: str, period_end: str,
    db_path: Path | None = None,
) -> dict:
    """Compare budgeted lines against actual for a period.

    Returns: per-category line items with planned/actual/variance.
    """
    lines = list_budget_lines(period_start=period_start, period_end=period_end,
                                db_path=db_path)
    out = []
    for line in lines:
        if line["direction"] == "expense":
            actuals = list_expenses(
                since=period_start, until=period_end,
                category=line["category"], db_path=db_path,
            )
            actual_cents = sum(e["amount_cents"] for e in actuals)
        else:
            # revenue line — sum revenue rows with matching source-or-category
            actuals = [
                r for r in list_revenue(since=period_start, db_path=db_path)
                if r["received_at"] <= period_end and r.get("source") == line["category"]
            ]
            actual_cents = sum(r["amount_cents"] for r in actuals)
        variance = actual_cents - line["planned_cents"]
        out.append({
            "category": line["category"],
            "direction": line["direction"],
            "planned_cents": line["planned_cents"],
            "actual_cents": actual_cents,
            "variance_cents": variance,
            "variance_pct": (
                round(variance / line["planned_cents"] * 100, 1)
                if line["planned_cents"] else None
            ),
        })
    return {
        "period_start": period_start, "period_end": period_end,
        "lines": out,
    }


__all__ = [
    "cash_position", "monthly_burn", "runway_months",
    "revenue_attribution_summary", "budget_vs_actual",
]
