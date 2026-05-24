# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
quality.db — continuous-score storage + rolling trust.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


QUALITY_DB_DEFAULT = STATE_DIR / "quality.db"
SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scored_artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id     TEXT NOT NULL,                   -- arbitrary: task_id, draft_path, prototype id, etc.
    producer        TEXT NOT NULL,                   -- which skill/profile made it
    artifact_kind   TEXT NOT NULL DEFAULT '',        -- draft | dossier | report | etc.
    overall_score   REAL NOT NULL,                   -- the lowest dimension score (a chain is as strong as its weakest)
    dimensions      TEXT NOT NULL DEFAULT '{}',      -- JSON {clarity: 0.9, specificity: 0.7, ...}
    scored_by       TEXT NOT NULL DEFAULT 'kb',      -- which skill scored it
    notes           TEXT NOT NULL DEFAULT '',
    scored_at       TEXT NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_sa_producer ON scored_artifacts(producer, scored_at);
CREATE INDEX IF NOT EXISTS idx_sa_artifact ON scored_artifacts(artifact_id);

CREATE TABLE IF NOT EXISTS producer_trust (
    producer        TEXT PRIMARY KEY,
    trust_state     TEXT NOT NULL DEFAULT 'trusted', -- trusted | watching | undelegated
    rolling_score   REAL NOT NULL DEFAULT 1.0,
    last_change_at  TEXT NOT NULL,
    last_change_reason TEXT NOT NULL DEFAULT '',
    note            TEXT NOT NULL DEFAULT ''
);
"""


@dataclass
class ScoredArtifact:
    id: int
    artifact_id: str
    producer: str
    artifact_kind: str
    overall_score: float
    dimensions: dict[str, float] = field(default_factory=dict)
    scored_by: str = ""
    notes: str = ""
    scored_at: str = ""


def init_quality_db(path: Path | None = None) -> Path:
    target = path or QUALITY_DB_DEFAULT
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
    init_quality_db(path)
    c = sqlite3.connect(str(path or QUALITY_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Score an artifact ───────────────────────────────────────────────────


def score_artifact(
    *, artifact_id: str, producer: str,
    dimensions: dict[str, float],
    scored_by: str = "kb", artifact_kind: str = "",
    notes: str = "", metadata: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Record a continuous score across dimensions.

    `dimensions` is operator-defined per artifact kind — typically
    `{"clarity": 0.9, "specificity": 0.7, "evidence_grounding": 0.85,
     "accessibility": 0.8}`. Values clamp to [0.0, 1.0].

    Overall score = the LOWEST dimension (a chain is as strong as
    its weakest link). Operators can override via the optional
    `overall_score` key in `metadata`.
    """
    clean = {k: max(0.0, min(1.0, float(v))) for k, v in dimensions.items()}
    overall = min(clean.values()) if clean else 0.0
    meta = metadata or {}
    if "overall_score" in meta:
        overall = float(meta["overall_score"])

    db = _conn(db_path)
    try:
        cur = db.execute(
            """
            INSERT INTO scored_artifacts (artifact_id, producer, artifact_kind,
                                            overall_score, dimensions, scored_by,
                                            notes, scored_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, producer, artifact_kind, overall,
             json.dumps(clean), scored_by, notes, _now(),
             json.dumps(meta)),
        )
        db.commit()
        # Trigger trust update for this producer
        _update_producer_trust(producer, db_path=db_path)
        return int(cur.lastrowid)
    finally:
        db.close()


def list_scores(
    *, producer: str | None = None, since_days: int = 30,
    db_path: Path | None = None,
) -> list[ScoredArtifact]:
    db = _conn(db_path)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
        if producer:
            rows = db.execute(
                "SELECT * FROM scored_artifacts WHERE producer=? AND scored_at>=? "
                "ORDER BY scored_at DESC",
                (producer, cutoff),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM scored_artifacts WHERE scored_at>=? ORDER BY scored_at DESC",
                (cutoff,),
            ).fetchall()
        return [_row_to_score(r) for r in rows]
    finally:
        db.close()


def _row_to_score(r: sqlite3.Row) -> ScoredArtifact:
    try:
        dims = json.loads(r["dimensions"] or "{}")
    except json.JSONDecodeError:
        dims = {}
    return ScoredArtifact(
        id=int(r["id"]),
        artifact_id=str(r["artifact_id"]),
        producer=str(r["producer"]),
        artifact_kind=str(r["artifact_kind"]),
        overall_score=float(r["overall_score"]),
        dimensions=dims,
        scored_by=str(r["scored_by"]),
        notes=str(r["notes"]),
        scored_at=str(r["scored_at"]),
    )


# ── Rolling score + trust ──────────────────────────────────────────────


def rolling_score(
    producer: str, *, window: int = 10,
    db_path: Path | None = None,
) -> dict:
    """Average overall_score across the producer's last N artifacts.

    Returns: {producer, count, mean_score, latest_n_scores}.
    """
    db = _conn(db_path)
    try:
        rows = db.execute(
            "SELECT overall_score, scored_at FROM scored_artifacts "
            "WHERE producer=? ORDER BY scored_at DESC LIMIT ?",
            (producer, window),
        ).fetchall()
    finally:
        db.close()
    scores = [float(r["overall_score"]) for r in rows]
    return {
        "producer": producer,
        "count": len(scores),
        "mean_score": (sum(scores) / len(scores)) if scores else None,
        "latest_n_scores": scores,
    }


def producer_trust(producer: str, db_path: Path | None = None) -> dict:
    db = _conn(db_path)
    try:
        row = db.execute("SELECT * FROM producer_trust WHERE producer=?",
                         (producer,)).fetchone()
        return dict(row) if row else {
            "producer": producer,
            "trust_state": "trusted",
            "rolling_score": 1.0,
            "last_change_at": "",
            "last_change_reason": "",
            "note": "",
        }
    finally:
        db.close()


def set_producer_trust(
    producer: str, *, trust_state: str, reason: str = "",
    note: str = "", db_path: Path | None = None,
) -> None:
    if trust_state not in ("trusted", "watching", "undelegated"):
        raise ValueError(f"invalid trust_state {trust_state!r}")
    db = _conn(db_path)
    try:
        roll = rolling_score(producer, db_path=db_path)
        db.execute(
            """
            INSERT INTO producer_trust (producer, trust_state, rolling_score,
                                          last_change_at, last_change_reason, note)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(producer) DO UPDATE SET
                trust_state = excluded.trust_state,
                rolling_score = excluded.rolling_score,
                last_change_at = excluded.last_change_at,
                last_change_reason = excluded.last_change_reason,
                note = excluded.note
            """,
            (producer, trust_state, roll.get("mean_score") or 1.0,
             _now(), reason, note),
        )
        db.commit()
    finally:
        db.close()


def _update_producer_trust(producer: str, db_path: Path | None = None) -> None:
    """Recompute the rolling-score field on producer_trust without
    changing trust_state. Trust state transitions are caller-driven
    (via `should_undelegate` → operator action)."""
    roll = rolling_score(producer, db_path=db_path)
    if roll["count"] == 0:
        return
    db = _conn(db_path)
    try:
        db.execute(
            """
            INSERT INTO producer_trust (producer, trust_state, rolling_score,
                                          last_change_at)
            VALUES (?, 'trusted', ?, ?)
            ON CONFLICT(producer) DO UPDATE SET
                rolling_score = excluded.rolling_score
            """,
            (producer, roll["mean_score"], _now()),
        )
        db.commit()
    finally:
        db.close()


__all__ = [
    "QUALITY_DB_DEFAULT", "ScoredArtifact",
    "init_quality_db",
    "score_artifact", "list_scores",
    "rolling_score", "producer_trust", "set_producer_trust",
]
