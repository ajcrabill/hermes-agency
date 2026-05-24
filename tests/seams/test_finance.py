"""Finance subsystem tests — invoices, expenses, revenue, budget, computations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.seam
def test_invoice_in_lifecycle(tmp_agency):
    from _framework.finance import (
        add_invoice_in, list_invoices_in, mark_invoice_in_paid,
    )
    iid = add_invoice_in(
        vendor="AWS", amount_cents=10000,
        vendor_invoice_id="AWS-2026-04-001",
        due_at="2026-05-01T00:00:00+00:00",
        category="infrastructure",
    )
    assert iid > 0
    unpaid = list_invoices_in(unpaid_only=True)
    assert len(unpaid) == 1
    mark_invoice_in_paid(iid)
    unpaid_after = list_invoices_in(unpaid_only=True)
    assert len(unpaid_after) == 0


@pytest.mark.seam
def test_invoice_out_with_revenue_link(tmp_agency):
    from _framework.finance import (
        add_invoice_out, list_invoices_out, mark_invoice_out_paid,
        add_revenue, list_revenue,
    )
    iid = add_invoice_out(
        client="Acme School District",
        our_invoice_id="HA-001",
        amount_cents=500000,
        due_at="2026-06-01T00:00:00+00:00",
    )
    rid = add_revenue(
        client="Acme School District",
        amount_cents=500000,
        invoice_out_id=iid,
        source="bd-outreach",
        source_detail="news-driven-2026-04",
    )
    invoices = list_invoices_out()
    assert invoices[0]["paid_at"] is not None
    assert invoices[0]["revenue_id"] == rid


@pytest.mark.seam
def test_expense_categorize(tmp_agency):
    from _framework.finance import (
        add_expense, list_expenses, categorize_expense,
    )
    eid = add_expense(
        amount_cents=2500,
        vendor="Stripe",
        description="processing fee",
    )
    expenses = list_expenses()
    assert expenses[0]["category"] == "uncategorized"

    categorize_expense(eid, category="payment-processing")
    after = list_expenses()
    assert after[0]["category"] == "payment-processing"


@pytest.mark.seam
def test_revenue_by_source_summary(tmp_agency):
    from _framework.finance import add_revenue, revenue_by_source
    add_revenue(client="A", amount_cents=100000, source="bd-outreach")
    add_revenue(client="B", amount_cents=200000, source="bd-outreach")
    add_revenue(client="C", amount_cents=50000, source="referral")
    sources = revenue_by_source()
    assert len(sources) == 2
    # bd-outreach > referral in dollars
    assert sources[0]["source"] == "bd-outreach"
    assert sources[0]["total_cents"] == 300000


@pytest.mark.seam
def test_cash_position_computation(tmp_agency):
    from _framework.finance import (
        add_revenue, add_expense, cash_position,
    )
    add_revenue(client="X", amount_cents=100000, source="referral")
    add_expense(amount_cents=30000, category="tools")
    pos = cash_position(opening_cents=500000)
    assert pos["opening_cents"] == 500000
    assert pos["revenue_cents"] == 100000
    assert pos["expense_cents"] == 30000
    assert pos["position_cents"] == 570000


@pytest.mark.seam
def test_monthly_burn(tmp_agency):
    from _framework.finance import add_expense, monthly_burn
    add_expense(amount_cents=10000, category="tools")
    add_expense(amount_cents=20000, category="hosting")
    burn = monthly_burn(months=1)
    assert burn["total_cents"] == 30000
    assert burn["monthly_avg_cents"] == 30000


@pytest.mark.seam
def test_runway_months(tmp_agency):
    from _framework.finance import add_expense, runway_months
    add_expense(amount_cents=10000, category="tools")
    add_expense(amount_cents=20000, category="hosting")
    rw = runway_months(cash_position_cents=300000, burn_window_months=1)
    # 300000 / 30000 = 10 months
    assert rw["months_remaining"] == 10.0


@pytest.mark.seam
def test_runway_undefined_when_no_burn(tmp_agency):
    from _framework.finance import runway_months
    rw = runway_months(cash_position_cents=500000, burn_window_months=1)
    assert rw["months_remaining"] == float("inf")


@pytest.mark.seam
def test_budget_vs_actual_expense_line(tmp_agency):
    from _framework.finance import (
        set_budget_line, add_expense, budget_vs_actual,
    )
    set_budget_line(
        period_start="2026-07-01", period_end="2026-09-30",
        category="tools", direction="expense", planned_cents=100000,
    )
    add_expense(
        amount_cents=120000, category="tools",
        occurred_at="2026-08-15T00:00:00+00:00",
    )
    report = budget_vs_actual(period_start="2026-07-01", period_end="2026-09-30")
    assert len(report["lines"]) == 1
    line = report["lines"][0]
    assert line["planned_cents"] == 100000
    assert line["actual_cents"] == 120000
    assert line["variance_cents"] == 20000   # over budget
    assert line["variance_pct"] == 20.0


@pytest.mark.seam
def test_overdue_detection(tmp_agency):
    from _framework.finance import (
        add_invoice_in, overdue_invoices_in,
    )
    past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    add_invoice_in(vendor="LateVendor", amount_cents=50000, due_at=past)
    overdue = overdue_invoices_in()
    assert len(overdue) == 1
    assert overdue[0]["vendor"] == "LateVendor"


@pytest.mark.seam
def test_attribution_summary_percentages(tmp_agency):
    from _framework.finance import add_revenue, revenue_attribution_summary
    add_revenue(client="A", amount_cents=750000, source="bd-outreach")
    add_revenue(client="B", amount_cents=250000, source="referral")
    summary = revenue_attribution_summary()
    assert summary["total_cents"] == 1000000
    by_src = {r["source"]: r for r in summary["by_source"]}
    assert by_src["bd-outreach"]["pct_of_total"] == 75.0
    assert by_src["referral"]["pct_of_total"] == 25.0
