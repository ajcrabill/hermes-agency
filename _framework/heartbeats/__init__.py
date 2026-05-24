# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Heartbeats — the lightest possible liveness signal.

Any script can `beat()` to record that it ran successfully.
Sentinel's `heartbeat_watch` cron reads from here and emits a
`heartbeat_stale` event when a component hasn't beat in 2× its
expected interval (cadence comes from
`invariants.yaml::expected_intervals_seconds`).

Public API:
  beat(component)         record a success
  beat_with_payload(...)  record + carry a small JSON blob
  recent(component=...)   query
  stale_components()      list of (component, last_success_at, age_sec)
"""

from .heartbeats import (
    beat,
    beat_with_payload,
    init_heartbeats_db,
    last_beat,
    recent,
    stale_components,
)

__all__ = [
    "beat",
    "beat_with_payload",
    "init_heartbeats_db",
    "last_beat",
    "recent",
    "stale_components",
]
