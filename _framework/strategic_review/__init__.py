# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Quarterly strategic-review-prep (v0.23.7).

Per StrategicPlanning.md §6.3 + spec §13.7 v0.23 Thread C #6:
the top-tier strategic review ("are these the *right* Outcomes?")
runs quarterly. This module produces the *packet* — the data the
Principal walks into the review meeting with.

The review meeting itself is Principal-driven. The CoS prepares;
the Principal decides.

The packet contains:

  1. Prior-quarter health-check trend (was the plan moving?)
  2. Audit findings summary (which alignment rules fired?)
  3. Firings rollup (which Initiatives produced output?)
  4. Three-layer structural review (mission → Outcomes →
     Interim Goals → Initiatives — what currently exists)
  5. A short checklist of questions the Principal should
     bring to the meeting

The packet is markdown — formatted for reading, not for a slide
deck. The Principal can print it, mark it up, and bring it to
the meeting.

Default cadence: first Monday of Jan / Apr / Jul / Oct. The
CoS's cron triggers `produce_review_packet()` and posts the
output to the Principal's kanban inbox.

Public API:

  produce_review_packet() -> ReviewPacket
  render_packet(packet: ReviewPacket) -> str
  is_quarterly_trigger_day(date) -> bool
"""

from .prep import (
    ReviewPacket,
    produce_review_packet,
    render_packet,
    is_quarterly_trigger_day,
    next_quarterly_trigger_date,
)

__all__ = [
    "ReviewPacket",
    "produce_review_packet",
    "render_packet",
    "is_quarterly_trigger_day",
    "next_quarterly_trigger_date",
]
