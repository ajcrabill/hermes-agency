# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment;
# customizations belong in ~/.agency/profiles/<P>/ or deployment.yaml.
"""
HermesAgency framework package.

Public surface is intentionally small: the CLI (`hermes_agency.cli`),
the `agency init` wizard (`_framework.ops.init`), and the subsystem
entry points (learning, autonomy, verifier, sentinel, send_guard, audit).

Deployments never import from this package directly; they invoke
through the `agency` CLI or via cron-fired skill loads.
"""

__version__ = "0.18.0"
