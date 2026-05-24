# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
v7 learning-corpus migration.

v7 schema (`~/.hermes/context/loriah/Admin/loriah.db::learning_rules`):
  id TEXT PK, ts TEXT, correction TEXT, skill_tags TEXT (JSON),
  source TEXT, context TEXT, status TEXT, replaced_by TEXT,
  notes TEXT, is_hard INTEGER

HermesAgency target (`learning.db::learning_rules`):
  id TEXT PK, correction TEXT, source TEXT, skill_tags TEXT,
  role_tags TEXT, voice_tags TEXT, is_hard INT, status TEXT,
  replaced_by TEXT, embedding BLOB, embedding_model TEXT,
  created_at TEXT, updated_at TEXT, notes TEXT

Translation:
  v7.id           → preserved (so v7-side audit references stay
                    intact; we can always look up "did this rule
                    migrate?")
  v7.ts           → created_at + updated_at (both)
  v7.correction   → correction
  v7.skill_tags   → skill_tags (already JSON; parsed + normalized)
  v7.source       → source (prefixed with "v7:" so origin is obvious)
  v7.context      → merged into notes
  v7.status       → status
  v7.replaced_by  → replaced_by
  v7.notes        → notes (combined with context)
  v7.is_hard      → is_hard
  (new)           → role_tags = []  (v7 didn't have this axis)
  (new)           → voice_tags = [] (v7 didn't have this axis)
  (new)           → embedding generated fresh via current embedder

The migration plan inspects each row + classifies its disposition:

  - migrate-fresh:    new to HermesAgency
  - already-present:  HermesAgency already has this id (re-run case)
  - skip-superseded:  v7 marked it superseded with no current value
  - skip-empty:       missing required fields
  - skip-dedup:       semantic duplicate of an existing HermesAgency
                      rule (matched by id OR exact correction text)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _framework.constants import HEALTH_DIR, LEARNING_DB


# ── Plan + result types ─────────────────────────────────────────────────


@dataclass
class V7RuleTranslation:
    """One v7 row's translation outcome (in the plan or the result)."""

    v7_id: str
    correction_preview: str            # first ~80 chars
    disposition: str                   # migrate-fresh | already-present | skip-* | applied | apply-failed
    target_id: str = ""                # the HermesAgency id (== v7.id on success)
    reason: str = ""
    skill_tags: list[str] = field(default_factory=list)
    is_hard: bool = False
    v7_status: str = "active"


@dataclass
class V7MigrationPlan:
    """The pre-apply summary."""

    source_db_path: str
    total_v7_rows: int
    translations: list[V7RuleTranslation] = field(default_factory=list)

    @property
    def to_migrate(self) -> list[V7RuleTranslation]:
        return [t for t in self.translations if t.disposition == "migrate-fresh"]

    @property
    def already_present(self) -> list[V7RuleTranslation]:
        return [t for t in self.translations if t.disposition == "already-present"]

    @property
    def skipped(self) -> list[V7RuleTranslation]:
        return [t for t in self.translations if t.disposition.startswith("skip-")]

    def summary(self) -> str:
        return (
            f"Total v7 rows:     {self.total_v7_rows}\n"
            f"  ✓ to migrate:    {len(self.to_migrate)}\n"
            f"  · already in HA: {len(self.already_present)}\n"
            f"  ⊘ skipped:       {len(self.skipped)}"
        )


@dataclass
class V7MigrationResult:
    """After apply runs — per-row outcomes."""

    plan: V7MigrationPlan
    applied: int = 0
    failed: int = 0
    failures: list[V7RuleTranslation] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.plan.summary()}\n"
            f"\n"
            f"After apply:\n"
            f"  ✓ applied:        {self.applied}\n"
            f"  ✗ failed:         {self.failed}"
        )


# ── Plan ─────────────────────────────────────────────────────────────────


def plan_v7_learning_migration(
    source_db_path: str | Path,
    *,
    target_db_path: Path | None = None,
) -> V7MigrationPlan:
    """Read v7's learning_rules + classify each row's disposition.
    No writes. Safe to run repeatedly."""
    src = Path(source_db_path).expanduser()
    if not src.exists():
        raise FileNotFoundError(f"v7 database not found at {src}")

    # Pull every v7 row
    sc = sqlite3.connect(str(src))
    sc.row_factory = sqlite3.Row
    v7_rows = sc.execute(
        "SELECT id, ts, correction, skill_tags, source, context, "
        "status, replaced_by, notes, is_hard FROM learning_rules"
    ).fetchall()
    sc.close()

    # Pull HermesAgency's known ids + corrections (for dedup)
    ha_ids: set[str] = set()
    ha_corrections: set[str] = set()
    target = target_db_path or LEARNING_DB
    if Path(target).exists():
        try:
            from _framework.learning.learning_db import get_db
            db = get_db(path=target)
            rows = db.execute("SELECT id, correction FROM learning_rules").fetchall()
            db.close()
            ha_ids = {r["id"] for r in rows}
            ha_corrections = {(r["correction"] or "").strip().lower() for r in rows}
        except Exception:
            # Target DB exists but unreadable — proceed as if empty;
            # apply step will fail loudly if there's a real issue.
            pass

    plan = V7MigrationPlan(source_db_path=str(src), total_v7_rows=len(v7_rows))

    for r in v7_rows:
        v7_id = str(r["id"] or "")
        correction = (r["correction"] or "").strip()
        preview = correction[:80] + ("…" if len(correction) > 80 else "")
        skill_tags = _parse_skill_tags(r["skill_tags"])
        is_hard = bool(r["is_hard"])
        v7_status = r["status"] or "active"

        t = V7RuleTranslation(
            v7_id=v7_id,
            correction_preview=preview,
            disposition="",
            target_id=v7_id,
            skill_tags=skill_tags,
            is_hard=is_hard,
            v7_status=v7_status,
        )

        if not v7_id or not correction:
            t.disposition = "skip-empty"
            t.reason = "missing id or correction"
        elif v7_status not in ("active", "suspended"):
            # superseded rules without a non-trivial value are noise
            if v7_status == "superseded" and not r["replaced_by"]:
                t.disposition = "skip-superseded"
                t.reason = f"v7 status={v7_status} with no replaced_by"
            else:
                # Preserve them — they're historically valuable
                t.disposition = "migrate-fresh"
        elif v7_id in ha_ids:
            t.disposition = "already-present"
            t.reason = "HA already has this id"
        elif correction.lower() in ha_corrections:
            t.disposition = "skip-dedup"
            t.reason = "HA already has an identical correction"
        else:
            t.disposition = "migrate-fresh"

        plan.translations.append(t)

    return plan


# ── Apply ────────────────────────────────────────────────────────────────


def apply_v7_learning_migration(
    plan: V7MigrationPlan,
    *,
    target_db_path: Path | None = None,
    write_journal: bool = True,
) -> V7MigrationResult:
    """Write `plan.to_migrate` rules into HermesAgency's learning.db.

    Uses the framework's `capture_correction` machinery so each migrated
    rule gets its embedding generated freshly + lands in the seven-step
    loop the same as a fresh capture. Source is prefixed with `v7:` so
    its origin stays obvious in any later audit.

    Idempotent: rows already present are skipped silently. Journaled
    to `_health/migration-journal.jsonl` per row.
    """
    from _framework.learning import capture_correction
    from _framework.learning.learning_db import get_db, encode_json_col

    target = target_db_path or LEARNING_DB
    result = V7MigrationResult(plan=plan)

    # Read v7 once again to get the full fields (plan only carries the
    # preview); we want the full correction + notes + context, etc.
    src = Path(plan.source_db_path).expanduser()
    sc = sqlite3.connect(str(src))
    sc.row_factory = sqlite3.Row
    v7_by_id = {
        r["id"]: r for r in sc.execute(
            "SELECT id, ts, correction, skill_tags, source, context, "
            "status, replaced_by, notes, is_hard FROM learning_rules"
        ).fetchall()
    }
    sc.close()

    journal_path = HEALTH_DIR / "migration-journal.jsonl"
    if write_journal:
        HEALTH_DIR.mkdir(parents=True, exist_ok=True)

    for t in plan.translations:
        if t.disposition != "migrate-fresh":
            _journal(t, "skipped-by-plan", journal_path, write_journal)
            continue

        v7_row = v7_by_id.get(t.v7_id)
        if not v7_row:
            t.disposition = "apply-failed"
            t.reason = "v7 row no longer present at apply time"
            result.failed += 1
            result.failures.append(t)
            _journal(t, "apply-failed", journal_path, write_journal)
            continue

        # Capture into HermesAgency (this generates embedding + writes
        # the row + runs recapture detection)
        try:
            capture_correction(
                correction=v7_row["correction"],
                source=f"v7:{v7_row['source']}" if v7_row["source"] else "v7:imported",
                skill_tags=_parse_skill_tags(v7_row["skill_tags"]) or ["general"],
                role_tags=[],
                voice_tags=[],
                is_hard=bool(v7_row["is_hard"]),
                notes=_merge_context_notes(v7_row["context"], v7_row["notes"]),
                db_path=target,
            )
            # capture_correction uses its own id-hash. Patch the row to
            # carry the v7 id forward so traceability holds.
            _backfill_v7_id(
                target_db=target, v7_id=t.v7_id,
                correction=v7_row["correction"], source=v7_row["source"] or "v7:imported",
                ts=v7_row["ts"], status=v7_row["status"] or "active",
                replaced_by=v7_row["replaced_by"] or None,
            )
            t.disposition = "applied"
            t.target_id = t.v7_id
            result.applied += 1
            _journal(t, "applied", journal_path, write_journal)
        except Exception as e:
            t.disposition = "apply-failed"
            t.reason = f"{type(e).__name__}: {e}"
            result.failed += 1
            result.failures.append(t)
            _journal(t, "apply-failed", journal_path, write_journal, error=str(e))

    return result


def _backfill_v7_id(
    *, target_db: Path, v7_id: str, correction: str, source: str,
    ts: str, status: str, replaced_by: str | None,
) -> None:
    """Update the just-captured row's id/timestamps/status to match the v7 row.

    `capture_correction` generated a new hash-based id. We want the
    v7.id preserved so audit references can cross-look-up. Match on
    (correction, source) which is unique per capture.
    """
    src_token = f"v7:{source}" if source else "v7:imported"
    db = sqlite3.connect(str(target_db))
    db.row_factory = sqlite3.Row
    try:
        row = db.execute(
            "SELECT id FROM learning_rules WHERE correction=? AND source=?",
            (correction.strip(), src_token),
        ).fetchone()
        if not row:
            return
        captured_id = row["id"]
        if captured_id == v7_id:
            return   # nothing to do
        # Conflicts: if v7_id already exists in HermesAgency, leave the
        # captured row as-is. Otherwise rename.
        existing = db.execute(
            "SELECT id FROM learning_rules WHERE id=?", (v7_id,),
        ).fetchone()
        if existing:
            return
        db.execute(
            "UPDATE learning_rules SET id=?, created_at=?, updated_at=?, "
            "status=?, replaced_by=? WHERE id=?",
            (v7_id, ts, ts, status, replaced_by or "", captured_id),
        )
        # Also fix any firings + recapture_events that reference the
        # captured id (shouldn't be any yet, but be safe)
        db.execute("UPDATE firings SET rule_id=? WHERE rule_id=?", (v7_id, captured_id))
        db.execute("UPDATE recapture_events SET new_rule_id=? WHERE new_rule_id=?", (v7_id, captured_id))
        db.execute("UPDATE recapture_events SET similar_to=? WHERE similar_to=?", (v7_id, captured_id))
        db.commit()
    finally:
        db.close()


def _journal(
    t: V7RuleTranslation, outcome: str, path: Path, write: bool,
    *, error: str = "",
) -> None:
    if not write:
        return
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": "v7-learning-migration",
        "v7_id": t.v7_id,
        "outcome": outcome,
        "disposition": t.disposition,
        "reason": t.reason,
        "preview": t.correction_preview,
    }
    if error:
        entry["error"] = error
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _parse_skill_tags(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw]
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(v, list):
            return [str(t) for t in v]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _merge_context_notes(context: str | None, notes: str | None) -> str:
    c = (context or "").strip()
    n = (notes or "").strip()
    if c and n:
        return f"{n}\n\n[v7-context] {c}"
    return n or c or ""


__all__ = [
    "V7MigrationPlan",
    "V7MigrationResult",
    "V7RuleTranslation",
    "plan_v7_learning_migration",
    "apply_v7_learning_migration",
]
