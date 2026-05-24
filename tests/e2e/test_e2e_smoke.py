"""
End-to-end smoke test.

Stands up a complete deployment shape in a temp dir using the real
scaffolds + spine modules. Exercises the v0.1 acceptance bar (§12.1
of HERMES_AGENCY_V0.1_SPEC.md) in a single test pass.
"""

from __future__ import annotations

import pytest


@pytest.mark.smoke
def test_minimal_deployment_end_to_end(tmp_agency):
    """
    Acceptance scenarios from §12.1 in narrow form:

      1. install location is set up
      2. scaffold three required profiles (CoS / KB / Sentinel)
      3. capture a correction → rule appears in learning.db
      4. recapture: capture the same correction again → recapture event
      5. audit-self → passes clean
      6. audit-profile on a freshly-scaffolded profile → at most warnings
    """
    # Imports happen after tmp_agency wires AGENCY_HOME
    from _framework.scaffolds import scaffold_profile
    from _framework.learning import capture_correction
    from _framework.learning.learning_db import get_db
    from _framework.audit import audit_self, audit_profile

    # 2. scaffold the three required roles
    scaffold_profile(role="chief-of-staff", profile_id="loriah", substitutions={
        "COS_NAME": "Loriah",
        "ORG_NAME": "AJ Crabill",
        "OWNER_NAME": "AJ",
        "COS_EMAIL": "loriah@example.com",
    })
    scaffold_profile(role="knowledge-base", profile_id="esby", substitutions={
        "KB_NAME": "Esby",
        "ORG_NAME": "AJ Crabill",
    })
    scaffold_profile(role="system-sentinel", profile_id="sentinel", substitutions={
        "SENTINEL_NAME": "Sentinel",
    })

    # 3. capture
    res = capture_correction(
        correction="A correction worth catching.",
        source="cli:e2e",
        skill_tags=["draft-composer"],
    )
    db = get_db()
    try:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM learning_rules WHERE id=?", (res.rule_id,),
        ).fetchone()
    finally:
        db.close()
    assert row["n"] == 1
    assert res.recapture is None

    # 4. recapture detection
    res2 = capture_correction(
        correction="A correction worth catching.",
        source="cli:e2e-take-2",
        skill_tags=["draft-composer"],
    )
    assert res2.recapture is not None
    assert res2.recapture.similar_to == res.rule_id

    # 5. framework self-audit clean
    self_report = audit_self()
    blocking = self_report.blocking_findings
    assert not blocking, f"unexpected framework-level blocking findings: {[str(b) for b in blocking]}"

    # 6. each scaffolded profile audits without blocking findings
    for prof in ("loriah", "esby", "sentinel"):
        report = audit_profile(profile=prof, strict=True)
        blocking = report.blocking_findings
        assert not blocking, f"profile {prof} has blocking findings: {[str(b) for b in blocking]}"
