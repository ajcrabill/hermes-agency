# SEAM TEST — owned by HermesAgency.
"""
`/agency capture --goal <key>` flag + goal_keys column (v0.23.8).

Verifies the flag parses correctly, the capture function persists
the keys on the learning rule, and the schema migration from v1 to
v2 is idempotent + non-destructive.
"""

from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    monkeypatch.setenv("HERMES_AGENCY_STATE", str(tmp_path / "_state"))
    for mod in [m for m in list(sys.modules) if m.startswith("_framework") or "hermes_agency_plugin" in m]:
        del sys.modules[mod]
    yield
    for mod in [m for m in list(sys.modules) if m.startswith("_framework") or "hermes_agency_plugin" in m]:
        del sys.modules[mod]


# ── Schema migration ───────────────────────────────────────────────────


def test_fresh_db_schema_includes_goal_keys_column(tmp_path):
    from _framework.learning.learning_db import init_learning_db

    db_path = tmp_path / "learning.db"
    init_learning_db(path=db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(learning_rules)"
        ).fetchall()}
    finally:
        conn.close()
    assert "goal_keys" in cols


def test_init_idempotent_on_v2_db(tmp_path):
    from _framework.learning.learning_db import init_learning_db
    db_path = tmp_path / "learning.db"
    init_learning_db(path=db_path)
    # Initialize again — must not raise + must not duplicate column
    init_learning_db(path=db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(learning_rules)"
        ).fetchall()]
    finally:
        conn.close()
    # No duplicate columns
    assert cols.count("goal_keys") == 1


def test_v1_db_migrates_to_v2_on_open(tmp_path):
    """Simulate an existing v1 DB (without goal_keys); opening it must
    apply the migration."""
    db_path = tmp_path / "learning.db"
    # Build the v1 schema by hand (omit goal_keys)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE learning_rules (
            id TEXT PRIMARY KEY, correction TEXT NOT NULL,
            source TEXT NOT NULL, skill_tags TEXT NOT NULL,
            role_tags TEXT, voice_tags TEXT,
            is_hard INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            replaced_by TEXT, embedding BLOB, embedding_model TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, notes TEXT
        );
        CREATE TABLE firings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL, skill_tag TEXT NOT NULL,
            profile TEXT NOT NULL, was_overridden INTEGER NOT NULL DEFAULT 0,
            action_summary TEXT, created_at TEXT NOT NULL
        );
        INSERT INTO meta(key, value) VALUES ('schema_version', '1');
    """)
    # A pre-existing row (proves migration is non-destructive)
    conn.execute(
        "INSERT INTO learning_rules (id, correction, source, skill_tags, "
        "created_at, updated_at) VALUES "
        "('test1', 'be more direct', 'pre-migration', "
        "'[\"general\"]', '2025-01-01T00:00:00', '2025-01-01T00:00:00')"
    )
    conn.commit()
    conn.close()

    # Now run init — should add goal_keys + bump schema_version
    from _framework.learning.learning_db import init_learning_db, SCHEMA_VERSION
    init_learning_db(path=db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(learning_rules)"
        ).fetchall()}
        version_row = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        # Pre-existing row is still there
        rows = conn.execute(
            "SELECT id, correction FROM learning_rules WHERE id='test1'"
        ).fetchall()
    finally:
        conn.close()
    assert "goal_keys" in cols
    assert int(version_row[0]) == SCHEMA_VERSION
    assert len(rows) == 1
    assert rows[0][1] == "be more direct"


# ── capture_correction(goal_keys=...) ──────────────────────────────────


def test_capture_correction_persists_goal_keys(tmp_path):
    from _framework.learning import capture_correction
    from _framework.learning.learning_db import row_to_rule
    import sqlite3

    db_path = tmp_path / "learning.db"
    result = capture_correction(
        correction="stop CCing Spencer on outreach emails",
        source="test",
        skill_tags=["cold-outreach"],
        goal_keys=["IG1.1", "skill:devon/cold-outreach-sender"],
        db_path=db_path,
    )
    assert result.goal_keys == ["IG1.1", "skill:devon/cold-outreach-sender"]

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM learning_rules WHERE id=?", (result.rule_id,)
        ).fetchone()
    finally:
        conn.close()
    rule = row_to_rule(row)
    assert rule["goal_keys"] == ["IG1.1", "skill:devon/cold-outreach-sender"]


def test_capture_correction_without_goal_keys_leaves_column_null(tmp_path):
    """Most corrections are stylistic — no goal_keys. The column
    stays NULL in that case (decoded as [])."""
    from _framework.learning import capture_correction
    from _framework.learning.learning_db import row_to_rule
    import sqlite3

    db_path = tmp_path / "learning.db"
    result = capture_correction(
        correction="be more direct in subject lines",
        source="test",
        skill_tags=["general"],
        db_path=db_path,
    )
    assert result.goal_keys == []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM learning_rules WHERE id=?", (result.rule_id,)
        ).fetchone()
    finally:
        conn.close()
    rule = row_to_rule(row)
    assert rule["goal_keys"] == []


def test_capture_correction_dedups_goal_keys(tmp_path):
    """Duplicate keys in the input are dropped."""
    from _framework.learning import capture_correction

    db_path = tmp_path / "learning.db"
    result = capture_correction(
        correction="test correction",
        source="test",
        skill_tags=["general"],
        goal_keys=["IG1.1", "IG1.1", "O1", " IG1.1 "],
        db_path=db_path,
    )
    assert result.goal_keys == ["IG1.1", "O1"]


# ── Command parsing ────────────────────────────────────────────────────


def test_split_capture_args_no_flags(tmp_path):
    from hermes_agency_plugin.commands import _split_capture_args
    text, keys = _split_capture_args('"stop CCing Spencer"')
    assert text == '"stop CCing Spencer"'
    assert keys == []


def test_split_capture_args_one_goal_flag(tmp_path):
    from hermes_agency_plugin.commands import _split_capture_args
    text, keys = _split_capture_args('"be more direct" --goal IG1.1')
    assert text == '"be more direct"'
    assert keys == ["IG1.1"]


def test_split_capture_args_multiple_goal_flags(tmp_path):
    from hermes_agency_plugin.commands import _split_capture_args
    text, keys = _split_capture_args(
        '"correction text" --goal O1 --goal IG1.1 --goal skill:devon/x'
    )
    assert text == '"correction text"'
    assert keys == ["O1", "IG1.1", "skill:devon/x"]


def test_agency_capture_command_attaches_goal_keys(tmp_path, monkeypatch):
    """End-to-end: `/agency capture "..." --goal IG1.1` lands a rule
    with the goal_keys persisted."""
    from hermes_agency_plugin.commands import handle_agency_command

    out = handle_agency_command(
        'capture "stop CCing Spencer on outreach" --goal IG1.1 '
        '--goal skill:devon/cold-outreach-sender'
    )
    assert out is not None
    assert "captured" in out.lower()
    assert "IG1.1" in out
    assert "skill:devon/cold-outreach-sender" in out

    # Verify it landed in the DB with the keys
    from _framework.constants import LEARNING_DB
    assert LEARNING_DB.exists()
    conn = sqlite3.connect(str(LEARNING_DB))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT goal_keys FROM learning_rules "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    import json
    keys = json.loads(row["goal_keys"])
    assert "IG1.1" in keys
    assert "skill:devon/cold-outreach-sender" in keys


def test_agency_capture_no_goal_flag_still_works(tmp_path, monkeypatch):
    """Capture without --goal still works (most corrections won't use it)."""
    from hermes_agency_plugin.commands import handle_agency_command
    out = handle_agency_command('capture "stylistic correction only"')
    assert "captured" in out.lower()
    # No 'Attached to' line because no keys
    assert "attached to" not in out.lower()


# ── Audit rule: goal-attribution-rate ─────────────────────────────────


def test_audit_goal_attribution_rate_emits_info_when_keys_present(tmp_path, monkeypatch):
    """When rules carry goal_keys, the audit's goal-attribution-rate
    rule emits an informational finding with the current rate."""
    from _framework.learning import capture_correction
    from _framework.audit.audit_alignment import _check_goal_attribution_rate

    capture_correction(
        correction="be more direct",
        source="test1",
        skill_tags=["general"],
        goal_keys=["IG1.1"],
    )
    capture_correction(
        correction="stop CCing Spencer",
        source="test2",
        skill_tags=["general"],
    )
    findings = _check_goal_attribution_rate()
    # Two rules total, one with keys → 50% rate, info-level
    assert findings
    assert findings[0].code == "goal-attribution-rate"
    assert findings[0].level == "info"
    assert "50%" in findings[0].message or "%" in findings[0].message


def test_audit_goal_attribution_rate_silent_below_50_rules(tmp_path, monkeypatch):
    """With fewer than 50 rules, the audit doesn't emit a 'rate is
    zero' warning. It still emits the info-level summary."""
    from _framework.learning import capture_correction
    from _framework.audit.audit_alignment import _check_goal_attribution_rate

    for i in range(5):
        capture_correction(
            correction=f"correction number {i}",
            source=f"test{i}",
            skill_tags=["general"],
        )
    findings = _check_goal_attribution_rate()
    # 5 rules, 0 with keys → info only, not warn
    assert findings
    assert findings[0].level == "info"
