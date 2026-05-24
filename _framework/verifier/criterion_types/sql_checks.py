# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""SQL-based criteria: sql_query (rowcount assertion against a sqlite DB)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from _framework.verifier.registry import register


@register("sql_query")
def sql_query(args: dict) -> tuple[bool, str]:
    """
    args:
      db:           path to sqlite db (str)
      query:        a SELECT statement (str)
      expect_rows:  expected rowcount (int, optional)
      expect_min:   minimum rowcount (int, optional)
      expect_max:   maximum rowcount (int, optional)

    At least one of expect_rows / expect_min / expect_max required.
    """
    db = args.get("db")
    query = args.get("query")
    if not db or not query:
        return False, "args.db and args.query required"
    p = Path(str(db)).expanduser()
    if not p.exists():
        return False, f"{p} not found"
    try:
        conn = sqlite3.connect(str(p))
        rows = conn.execute(query).fetchall()
        conn.close()
    except Exception as e:
        return False, f"query failed: {e}"
    n = len(rows)

    if "expect_rows" in args:
        want = int(args["expect_rows"])
        if n == want:
            return True, f"query returned {n} row(s) (matches expect_rows={want})"
        return False, f"query returned {n} row(s), expected {want}"
    if "expect_min" in args:
        want = int(args["expect_min"])
        if n < want:
            return False, f"query returned {n} row(s), needed >= {want}"
    if "expect_max" in args:
        want = int(args["expect_max"])
        if n > want:
            return False, f"query returned {n} row(s), needed <= {want}"
    if "expect_min" in args or "expect_max" in args:
        return True, f"query returned {n} row(s) (within range)"
    return False, "no expect_rows / expect_min / expect_max provided"
