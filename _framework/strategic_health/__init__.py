# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Strategic-plan health check (v0.23.6).

Per StrategicPlanning.md §7.4 + spec §1.7 mid-tier weekly cadence,
the CoS runs a weekly health check that asks three questions:

  1. For each Outcome: is the lagging indicator moving in the right
     direction at the expected pace? (Often the data isn't there yet
     — that's a signal too.)
  2. For each Interim Goal: is the SMART metric on track?
  3. For each Initiative: are the firings happening on cadence?
     Are the artifacts being produced?

The point is *pivoting*: the output is a short summary that names the
one or two things that have drifted and proposes a pivot. The plan is
a tool for pivoting, not for self-congratulation.

This module produces structured data; the CoS skill renders it into
plain-language prose for the Principal.

Public API:

  run_health_check() -> HealthReport
      Read Goals.md (three-layer) + goal_tracking DB + firings DB +
      audit findings, produce a structured report.

  render_report(report: HealthReport) -> str
      Render a HealthReport as plain-language markdown the Principal
      can read in under 60 seconds.
"""

from .check import (
    HealthReport,
    OutcomeHealth,
    InterimGoalHealth,
    InitiativeHealth,
    run_health_check,
    render_report,
)

__all__ = [
    "HealthReport",
    "OutcomeHealth",
    "InterimGoalHealth",
    "InitiativeHealth",
    "run_health_check",
    "render_report",
]
