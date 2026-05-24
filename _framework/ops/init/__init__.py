# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
agency init wizard.

Three tiers per spec Appendix A.1:

  Tier 1 (5-10 min) "Just defaults"      — required fields only
  Tier 2 (15-30 min) "Recommended"        — OAuth + ingress config
  Tier 3 (45-60 min) "Power user / deep"  — exemplar capture, IP import

Public entry: `run_wizard(tier=1)`. The CLI's `agency init` calls
this.
"""

from .wizard import run_wizard

__all__ = ["run_wizard"]
