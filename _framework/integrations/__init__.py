# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
External service integrations (Google Drive, Calendar, etc.).

Each integration is OPTIONAL — the framework boots without any of
them. When a deployment opts in, the integration becomes available
via its module's public API.

Available in v0.2:
  google_drive — file upload + share via Drive API

Pattern: each integration has a `setup_<name>()` helper that walks
the operator through credential acquisition (OAuth flow URL, etc.),
and an action surface that other code calls.
"""

from . import google_drive
from . import google_calendar
from . import gmail

__all__ = ["google_drive", "google_calendar", "gmail"]
