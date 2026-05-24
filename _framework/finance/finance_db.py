# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
finance.db — invoices, expenses, revenue, budget, vendor payments.

Amounts stored as integers in CENTS (or whatever smallest unit the
operator's currency uses). Avoids float rounding drift across
thousands of operations. Display layer divides by 100 to show.

Currency code is per-row (operators may transact in multiple
currencies; the framework doesn't convert — that's a deployment
concern with its own FX-rate policy).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


FINANCE_DB_DEFAULT = STATE_DIR / "finance.db"
SCHEMA_VERSION = 1


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices_in (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor          TEXT NOT NULL,
    vendor_invoice_id TEXT,                       -- the vendor's own invoice id
    amount_cents    INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    received_at     TEXT NOT NULL,
    due_at          TEXT,
    paid_at         TEXT,
    category        TEXT NOT NULL DEFAULT 'uncategorized',
    description     TEXT NOT NULL DEFAULT '',
    source_msg_id   TEXT,                          -- if extracted from inbox
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_inv_in_due ON invoices_in(due_at, paid_at);
CREATE INDEX IF NOT EXISTS idx_inv_in_vendor ON invoices_in(vendor);

CREATE TABLE IF NOT EXISTS invoices_out (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client          TEXT NOT NULL,
    our_invoice_id  TEXT,                          -- the number we assign
    amount_cents    INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    sent_at         TEXT NOT NULL,
    due_at          TEXT,
    paid_at         TEXT,
    category        TEXT NOT NULL DEFAULT 'services',
    description     TEXT NOT NULL DEFAULT '',
    revenue_id      INTEGER,                       -- once paid, links to revenue row
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_inv_out_due ON invoices_out(due_at, paid_at);
CREATE INDEX IF NOT EXISTS idx_inv_out_client ON invoices_out(client);

CREATE TABLE IF NOT EXISTS expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at     TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    category        TEXT NOT NULL DEFAULT 'uncategorized',
    vendor          TEXT,
    description     TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT 'manual',  -- manual | bank-import | card-import | invoice-import
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_exp_when ON expenses(occurred_at);
CREATE INDEX IF NOT EXISTS idx_exp_cat ON expenses(category, occurred_at);

CREATE TABLE IF NOT EXISTS revenue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at     TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    client          TEXT NOT NULL,
    invoice_out_id  INTEGER REFERENCES invoices_out(id),
    source          TEXT NOT NULL DEFAULT 'unattributed',
                                                    -- e.g. bd-outreach | journalist-pitch |
                                                    -- referral | inbound | renewal
    source_detail   TEXT NOT NULL DEFAULT '',       -- e.g. specific outreach id
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_rev_when ON revenue(received_at);
CREATE INDEX IF NOT EXISTS idx_rev_client ON revenue(client);

CREATE TABLE IF NOT EXISTS vendor_payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor          TEXT NOT NULL,
    invoice_in_id   INTEGER REFERENCES invoices_in(id),
    amount_cents    INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    paid_at         TEXT NOT NULL,
    method          TEXT NOT NULL DEFAULT 'ach',
    confirmation    TEXT,
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_vp_vendor ON vendor_payments(vendor, paid_at);

CREATE TABLE IF NOT EXISTS budget_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start    TEXT NOT NULL,                  -- e.g. '2026-Q3' or '2026-07-01'
    period_end      TEXT NOT NULL,
    category        TEXT NOT NULL,
    direction       TEXT NOT NULL,                  -- 'expense' | 'revenue'
    planned_cents   INTEGER NOT NULL,
    note            TEXT NOT NULL DEFAULT '',
    UNIQUE(period_start, period_end, category, direction)
);
CREATE INDEX IF NOT EXISTS idx_bud_period ON budget_lines(period_start, period_end);
"""


def init_finance_db(path: Path | None = None) -> Path:
    target = path or FINANCE_DB_DEFAULT
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(SCHEMA_V1)
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
        conn.commit()
    finally:
        conn.close()
    return target


def _conn(path: Path | None = None) -> sqlite3.Connection:
    init_finance_db(path)
    c = sqlite3.connect(str(path or FINANCE_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Invoices IN ─────────────────────────────────────────────────────────


def add_invoice_in(
    *, vendor: str, amount_cents: int,
    vendor_invoice_id: str | None = None,
    currency: str = "USD",
    received_at: str | None = None, due_at: str | None = None,
    category: str = "uncategorized", description: str = "",
    source_msg_id: str | None = None,
    metadata: dict | None = None, db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO invoices_in (vendor, vendor_invoice_id, amount_cents,
                                       currency, received_at, due_at, category,
                                       description, source_msg_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (vendor, vendor_invoice_id, amount_cents, currency,
             received_at or _now(), due_at, category, description,
             source_msg_id, json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def list_invoices_in(*, vendor: str | None = None, unpaid_only: bool = False,
                      db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        conditions = []
        params: list[Any] = []
        if vendor:
            conditions.append("vendor=?")
            params.append(vendor)
        if unpaid_only:
            conditions.append("paid_at IS NULL")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = db.execute(
            f"SELECT * FROM invoices_in{where} ORDER BY due_at NULLS LAST",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def mark_invoice_in_paid(invoice_id: int, *, paid_at: str | None = None,
                          db_path: Path | None = None) -> None:
    db = _conn(db_path)
    try:
        db.execute(
            "UPDATE invoices_in SET paid_at=? WHERE id=?",
            (paid_at or _now(), invoice_id),
        )
        db.commit()
    finally:
        db.close()


def overdue_invoices_in(db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT * FROM invoices_in WHERE paid_at IS NULL AND due_at < ? "
            "ORDER BY due_at",
            (_now(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Invoices OUT ────────────────────────────────────────────────────────


def add_invoice_out(
    *, client: str, amount_cents: int,
    our_invoice_id: str | None = None,
    currency: str = "USD",
    sent_at: str | None = None, due_at: str | None = None,
    category: str = "services", description: str = "",
    metadata: dict | None = None, db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO invoices_out (client, our_invoice_id, amount_cents,
                                        currency, sent_at, due_at, category,
                                        description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (client, our_invoice_id, amount_cents, currency,
             sent_at or _now(), due_at, category, description,
             json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def list_invoices_out(*, client: str | None = None, unpaid_only: bool = False,
                       db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        conditions = []
        params: list[Any] = []
        if client:
            conditions.append("client=?")
            params.append(client)
        if unpaid_only:
            conditions.append("paid_at IS NULL")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = db.execute(
            f"SELECT * FROM invoices_out{where} ORDER BY due_at NULLS LAST",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def mark_invoice_out_paid(
    invoice_id: int, *, paid_at: str | None = None,
    revenue_id: int | None = None, db_path: Path | None = None,
) -> None:
    db = _conn(db_path)
    try:
        db.execute(
            "UPDATE invoices_out SET paid_at=?, revenue_id=? WHERE id=?",
            (paid_at or _now(), revenue_id, invoice_id),
        )
        db.commit()
    finally:
        db.close()


def overdue_invoices_out(db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT * FROM invoices_out WHERE paid_at IS NULL AND due_at < ? "
            "ORDER BY due_at",
            (_now(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Expenses ────────────────────────────────────────────────────────────


def add_expense(
    *, amount_cents: int, occurred_at: str | None = None,
    currency: str = "USD", category: str = "uncategorized",
    vendor: str | None = None, description: str = "",
    source: str = "manual", metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO expenses (occurred_at, amount_cents, currency, category,
                                    vendor, description, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (occurred_at or _now(), amount_cents, currency, category,
             vendor, description, source, json.dumps(metadata or {})),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def list_expenses(
    *, since: str | None = None, until: str | None = None,
    category: str | None = None, db_path: Path | None = None,
) -> list[dict]:
    db = _conn(db_path)
    try:
        conditions = []
        params: list[Any] = []
        if since:
            conditions.append("occurred_at >= ?")
            params.append(since)
        if until:
            conditions.append("occurred_at <= ?")
            params.append(until)
        if category:
            conditions.append("category=?")
            params.append(category)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = db.execute(
            f"SELECT * FROM expenses{where} ORDER BY occurred_at DESC", params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def categorize_expense(expense_id: int, *, category: str,
                        db_path: Path | None = None) -> None:
    db = _conn(db_path)
    try:
        db.execute(
            "UPDATE expenses SET category=? WHERE id=?",
            (category, expense_id),
        )
        db.commit()
    finally:
        db.close()


# ── Revenue ─────────────────────────────────────────────────────────────


def add_revenue(
    *, client: str, amount_cents: int,
    received_at: str | None = None, currency: str = "USD",
    invoice_out_id: int | None = None,
    source: str = "unattributed", source_detail: str = "",
    metadata: dict | None = None, db_path: Path | None = None,
) -> int:
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO revenue (received_at, amount_cents, currency, client,
                                  invoice_out_id, source, source_detail, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (received_at or _now(), amount_cents, currency, client,
             invoice_out_id, source, source_detail, json.dumps(metadata or {})),
        )
        rev_id = int(cur.lastrowid)
        if invoice_out_id:
            db.execute(
                "UPDATE invoices_out SET revenue_id=?, paid_at=COALESCE(paid_at, ?) "
                "WHERE id=?",
                (rev_id, received_at or _now(), invoice_out_id),
            )
        db.commit()
        return rev_id
    finally:
        db.close()


def list_revenue(*, since: str | None = None, db_path: Path | None = None) -> list[dict]:
    db = _conn(db_path)
    try:
        if since:
            rows = db.execute(
                "SELECT * FROM revenue WHERE received_at >= ? ORDER BY received_at DESC",
                (since,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM revenue ORDER BY received_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def revenue_by_source(
    *, since: str | None = None, db_path: Path | None = None,
) -> list[dict]:
    """Group revenue by source. Returns [{'source':..., 'total_cents':..., 'count':...}]."""
    db = _conn(db_path)
    try:
        if since:
            rows = db.execute(
                "SELECT source, SUM(amount_cents) AS total_cents, COUNT(*) AS n "
                "FROM revenue WHERE received_at >= ? GROUP BY source ORDER BY total_cents DESC",
                (since,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT source, SUM(amount_cents) AS total_cents, COUNT(*) AS n "
                "FROM revenue GROUP BY source ORDER BY total_cents DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ── Budget ──────────────────────────────────────────────────────────────


def set_budget_line(
    *, period_start: str, period_end: str, category: str,
    direction: str, planned_cents: int, note: str = "",
    db_path: Path | None = None,
) -> int:
    """Set/update a budget line. Direction is 'expense' or 'revenue'."""
    if direction not in ("expense", "revenue"):
        raise ValueError(f"direction must be expense|revenue, got {direction!r}")
    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO budget_lines (period_start, period_end, category, direction,
                                       planned_cents, note)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(period_start, period_end, category, direction) DO UPDATE SET
                planned_cents = excluded.planned_cents,
                note = excluded.note
            """,
            (period_start, period_end, category, direction, planned_cents, note),
        )
        db.commit()
        return int(cur.lastrowid)
    finally:
        db.close()


def get_budget_line(
    *, period_start: str, period_end: str, category: str, direction: str,
    db_path: Path | None = None,
) -> dict | None:
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT * FROM budget_lines WHERE period_start=? AND period_end=? "
            "AND category=? AND direction=?",
            (period_start, period_end, category, direction),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def list_budget_lines(
    *, period_start: str | None = None, period_end: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    db = _conn(db_path)
    try:
        conditions = []
        params: list[Any] = []
        if period_start:
            conditions.append("period_start=?")
            params.append(period_start)
        if period_end:
            conditions.append("period_end=?")
            params.append(period_end)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = db.execute(
            f"SELECT * FROM budget_lines{where} ORDER BY period_start, direction, category",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


__all__ = [
    "FINANCE_DB_DEFAULT", "SCHEMA_VERSION",
    "init_finance_db",
    "add_invoice_in", "list_invoices_in", "mark_invoice_in_paid",
    "overdue_invoices_in",
    "add_invoice_out", "list_invoices_out", "mark_invoice_out_paid",
    "overdue_invoices_out",
    "add_expense", "list_expenses", "categorize_expense",
    "add_revenue", "list_revenue", "revenue_by_source",
    "set_budget_line", "get_budget_line", "list_budget_lines",
]
