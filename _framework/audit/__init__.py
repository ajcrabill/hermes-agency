# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Audit subsystem — the framework's self-check + skill audit.

`audit_alignment.py` is the engine. Rules live there, organized by
the 7-category playbook taxonomy (§9 of DEVELOPMENT_PLAYBOOK):

  1. Skill anatomy        — frontmatter, required sections
  2. Skill discipline     — verifier wired, supervised learning,
                            action surface, untrusted-content guards
  3. Script anatomy       — shebang, error handling, secrets
  4. Profile structure    — SOUL.md, standards.md, persona files
  5. Cross-profile        — role-mismatch, kanban tenant validity
  6. Learning loop        — loop-broken, recapture-implicates,
                            untagged rules
  7. Framework integrity  — vendor leak, deprecated paths,
                            injection-trigger discipline

Modes:
  - `audit_skill(skill, profile)`     focused single-skill audit
  - `audit_profile(profile)`           every skill + scripts in a profile
  - `audit_deployment()`               full fleet audit
  - `audit_self()`                     audits the framework against itself
                                       (no deployment required)

`--strict` flag suppresses warnings — only ALWAYS_BLOCK findings count
toward the result, which is what the graduation gate uses.
"""

from . import audit_alignment
from .audit_alignment import (
    AuditFinding,
    AuditReport,
    audit_skill,
    audit_profile,
    audit_deployment,
    audit_self,
)

__all__ = [
    "AuditFinding",
    "AuditReport",
    "audit_skill",
    "audit_profile",
    "audit_deployment",
    "audit_self",
    "audit_alignment",
]
