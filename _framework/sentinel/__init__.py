# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Sentinel — pure observability. Read-only authority.

The agent that watches the agency. Watches the learning loop's
integrity, the per-cron heartbeats, the drift score per skill, and
the audit report's findings over time.

Sentinel never mutates state outside her own events table. She can
file kanban tasks (tenant=alert / audit / compliance / recapture) —
that's how she notifies the owner — but she never sends mail, edits
skills, restarts services, or changes autonomy state.

Public API (the things Sentinel's cron jobs and other subsystems
call):

  events.append(kind, actor, target, severity, payload)
  events.recent(kind=..., since=..., limit=...)
  monitors.learning_monitor()    runs every 5m via cron
  monitors.drift_monitor()       runs every 15m via cron
  monitors.heartbeat_watch()     runs every 5m via cron
  monitors.event_rollup()        runs hourly via cron

The cron entry points all delegate to these.
"""

from .events_db import (
    init_events_db,
    append as append_event,
    recent as recent_events,
)
from . import monitors

__all__ = [
    "init_events_db",
    "append_event",
    "recent_events",
    "monitors",
]
