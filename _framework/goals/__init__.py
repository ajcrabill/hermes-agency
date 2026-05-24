# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Goals module — Goals.md round-trip + SMART criteria.

Goals.md is the single most important document the agency reads.
Agents need a structured way to:

  - Read parsed sections (so they can answer "what are the active
    projects?" without re-parsing markdown every call)
  - Add a new goal (with interim milestones as sub-bullets)
  - Replace or refine an existing goal
  - Validate that a goal meets SMART criteria before adding it

The file itself stays human-readable + human-editable. Agents are
disciplined editors: they preserve the operator's structure and
prose; they only edit the section they're operating on.

Public API:

  read_goals()                          → ParsedGoals
  add_annual_goal(text, interim=[...])
  replace_annual_goal(index, text, interim=[...])
  add_active_project(text, details=...)
  smart_check(goal_text)                → SmartVerdict
"""

from .goals_md import (
    ParsedGoals,
    read_goals,
    add_annual_goal,
    replace_annual_goal,
    add_active_project,
    SECTION_HEADERS,
)
from .smart import smart_check, SmartVerdict
from .tracking import (
    init_goal_tracking_db,
    define_metric, list_metrics,
    record_observation, latest_observation, observation_history,
    metric_status, weekly_status_report,
    upsert_milestone, mark_milestone, list_milestones,
    sync_milestones_from_goals_md,
    GoalMetric,
)

__all__ = [
    "ParsedGoals", "read_goals",
    "add_annual_goal", "replace_annual_goal", "add_active_project",
    "SECTION_HEADERS",
    "smart_check", "SmartVerdict",
    "init_goal_tracking_db",
    "define_metric", "list_metrics",
    "record_observation", "latest_observation", "observation_history",
    "metric_status", "weekly_status_report",
    "upsert_milestone", "mark_milestone", "list_milestones",
    "sync_milestones_from_goals_md",
    "GoalMetric",
]
