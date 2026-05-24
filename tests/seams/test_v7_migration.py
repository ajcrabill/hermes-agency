"""v7 migration tests — plan + apply with a synthetic v7 database."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _make_v7_db(tmp_path) -> Path:
    """Build a tiny v7-shaped database for testing."""
    db_path = tmp_path / "v7.db"
    c = sqlite3.connect(str(db_path))
    c.executescript("""
        CREATE TABLE learning_rules (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            correction TEXT NOT NULL,
            skill_tags TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT '',
            context TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            replaced_by TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            is_hard INTEGER DEFAULT 0
        );
    """)
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        ("v7id001", now, "Always lead with the agency's craft, not the metrics.",
         json.dumps(["draft-composer"]), "ajc-email-2026-04-12",
         "context A", "active", "", "first batch", 0),
        ("v7id002", now, "Never CC the board without a heads-up.",
         json.dumps(["send-orchestrator"]), "ajc-email-2026-04-15",
         "", "active", "", "", 1),  # hard rule
        ("v7id003", now, "Old rule that was superseded.",
         json.dumps(["draft-composer"]), "ajc-old-source",
         "", "superseded", "", "", 0),  # superseded with no replacement
        ("v7id004", now, "",   # empty correction → skip
         json.dumps(["foo"]), "test", "", "active", "", "", 0),
    ]
    c.executemany(
        "INSERT INTO learning_rules (id, ts, correction, skill_tags, source, "
        "context, status, replaced_by, notes, is_hard) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    c.commit()
    c.close()
    return db_path


@pytest.mark.seam
def test_plan_classifies_dispositions(tmp_path, tmp_agency):
    from _framework.migration import plan_v7_learning_migration
    src = _make_v7_db(tmp_path)
    plan = plan_v7_learning_migration(src)
    assert plan.total_v7_rows == 4
    dispositions = {t.v7_id: t.disposition for t in plan.translations}
    assert dispositions["v7id001"] == "migrate-fresh"
    assert dispositions["v7id002"] == "migrate-fresh"
    assert dispositions["v7id003"] == "skip-superseded"
    assert dispositions["v7id004"] == "skip-empty"

    assert len(plan.to_migrate) == 2
    assert len(plan.skipped) == 2


@pytest.mark.seam
def test_apply_migrates_active_rules(tmp_path, tmp_agency):
    from _framework.migration import (
        plan_v7_learning_migration, apply_v7_learning_migration,
    )
    from _framework.learning.learning_db import get_db

    src = _make_v7_db(tmp_path)
    plan = plan_v7_learning_migration(src)
    result = apply_v7_learning_migration(plan)

    assert result.applied == 2
    assert result.failed == 0

    # Verify the rules landed in HermesAgency's learning.db with v7 ids
    # preserved
    db = get_db()
    rows = db.execute(
        "SELECT id, correction, source, is_hard FROM learning_rules "
        "ORDER BY id"
    ).fetchall()
    db.close()
    ids = {r["id"] for r in rows}
    assert "v7id001" in ids
    assert "v7id002" in ids
    sources = {r["source"] for r in rows}
    assert any(s.startswith("v7:") for s in sources)
    # The hard rule survived
    hard_count = sum(1 for r in rows if int(r["is_hard"]) == 1)
    assert hard_count == 1


@pytest.mark.seam
def test_apply_is_idempotent(tmp_path, tmp_agency):
    """Running apply twice doesn't double-insert."""
    from _framework.migration import (
        plan_v7_learning_migration, apply_v7_learning_migration,
    )
    from _framework.learning.learning_db import get_db

    src = _make_v7_db(tmp_path)
    apply_v7_learning_migration(plan_v7_learning_migration(src))
    apply_v7_learning_migration(plan_v7_learning_migration(src))

    db = get_db()
    rows = db.execute(
        "SELECT COUNT(*) AS n FROM learning_rules WHERE id LIKE 'v7id%'"
    ).fetchone()
    db.close()
    # 2 active rules, 1 superseded if we'd migrated it (we didn't),
    # 1 empty (skipped) — so 2 distinct ids in HA from v7
    assert rows["n"] == 2


@pytest.mark.seam
def test_apply_journals_outcomes(tmp_path, tmp_agency):
    from _framework.migration import (
        plan_v7_learning_migration, apply_v7_learning_migration,
    )
    from _framework.constants import HEALTH_DIR

    src = _make_v7_db(tmp_path)
    apply_v7_learning_migration(plan_v7_learning_migration(src))
    journal = HEALTH_DIR / "migration-journal.jsonl"
    assert journal.exists()
    lines = [
        json.loads(line) for line in journal.read_text().splitlines()
        if line.strip()
    ]
    # 4 v7 rows → 4 journal entries
    assert len(lines) == 4
    outcomes = {e["v7_id"]: e["outcome"] for e in lines}
    assert outcomes["v7id001"] == "applied"
    assert outcomes["v7id002"] == "applied"
    assert outcomes["v7id003"] == "skipped-by-plan"
    assert outcomes["v7id004"] == "skipped-by-plan"


@pytest.mark.seam
def test_plan_against_missing_db_raises(tmp_path, tmp_agency):
    from _framework.migration import plan_v7_learning_migration
    with pytest.raises(FileNotFoundError):
        plan_v7_learning_migration(tmp_path / "nonexistent.db")


@pytest.mark.seam
def test_plan_after_apply_shows_already_present(tmp_path, tmp_agency):
    from _framework.migration import (
        plan_v7_learning_migration, apply_v7_learning_migration,
    )
    src = _make_v7_db(tmp_path)
    apply_v7_learning_migration(plan_v7_learning_migration(src))
    # Second plan should see them as already-present
    second = plan_v7_learning_migration(src)
    dispositions = {t.v7_id: t.disposition for t in second.translations}
    assert dispositions["v7id001"] == "already-present"
    assert dispositions["v7id002"] == "already-present"
