# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Scaffold generators — playbook-compliant artifact creation.

  - scaffold_skill(name, profile, role, ...)  → SKILL.md
  - scaffold_script(name, profile, ...)        → <name>.py
  - scaffold_profile(role, id, ...)            → full profile dir
"""

from .scaffold_skill import scaffold_skill
from .scaffold_script import scaffold_script
from .scaffold_profile import scaffold_profile

__all__ = ["scaffold_skill", "scaffold_script", "scaffold_profile"]
