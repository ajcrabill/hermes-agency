# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Google Calendar integration — list / create / update / delete events,
conflict detection.

Same pattern as `google_drive`: lazy-imported runtime client, profile-
local credentials, optional Python deps. The framework boots without
the Google libraries installed; operators add them when they want
this integration.

Setup:
  agency integrations google-calendar setup \\
      --profile <cos-id> \\
      --client-secret /path/to/client_secret.json

Token storage: `profiles/<cos-id>/credentials/google_calendar_token.json`.

Runtime use:
  from _framework.integrations.google_calendar import list_events, create_event
  events = list_events(profile=cos_id, time_min=..., time_max=...)
  ev_id  = create_event(profile=cos_id, summary=..., start=..., end=...)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import profile_dir


GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def credentials_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "google_calendar_token.json"


def client_secret_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "google_calendar_client_secret.json"


def is_configured(profile: str) -> bool:
    return credentials_path(profile).exists()


@dataclass
class CalendarEvent:
    id: str
    summary: str
    start: str           # ISO8601
    end: str
    attendees: list[str]
    location: str = ""
    description: str = ""
    html_link: str = ""


def list_events(
    profile: str,
    *,
    time_min: str | None = None,
    time_max: str | None = None,
    calendar_id: str = "primary",
    max_results: int = 50,
) -> list[CalendarEvent]:
    """Return events in the time window."""
    if not is_configured(profile):
        raise RuntimeError(
            f"Google Calendar not configured for profile '{profile}'. "
            f"Run: agency integrations google-calendar setup --profile {profile}"
        )
    client = _runtime_client(profile)
    cal = client["build"]("calendar", "v3", credentials=client["creds"])
    params = {
        "calendarId": calendar_id,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max
    resp = cal.events().list(**params).execute()
    out: list[CalendarEvent] = []
    for e in resp.get("items", []):
        start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date") or ""
        end = e.get("end", {}).get("dateTime") or e.get("end", {}).get("date") or ""
        attendees = [a.get("email", "") for a in e.get("attendees", []) if a.get("email")]
        out.append(CalendarEvent(
            id=e.get("id", ""),
            summary=e.get("summary", ""),
            start=start, end=end,
            attendees=attendees,
            location=e.get("location", ""),
            description=e.get("description", ""),
            html_link=e.get("htmlLink", ""),
        ))
    return out


def create_event(
    profile: str,
    *,
    summary: str,
    start: str,
    end: str,
    description: str = "",
    location: str = "",
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
    send_notifications: bool = False,
) -> str:
    """Create an event. `start`/`end` are ISO8601 with timezone. Returns event id."""
    if not is_configured(profile):
        raise RuntimeError(
            f"Google Calendar not configured for profile '{profile}'."
        )
    client = _runtime_client(profile)
    cal = client["build"]("calendar", "v3", credentials=client["creds"])
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "attendees": [{"email": a} for a in (attendees or [])],
    }
    resp = cal.events().insert(
        calendarId=calendar_id, body=body,
        sendNotifications=send_notifications,
    ).execute()
    return resp.get("id", "")


def update_event(
    profile: str, event_id: str,
    *,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> None:
    if not is_configured(profile):
        raise RuntimeError(
            f"Google Calendar not configured for profile '{profile}'."
        )
    client = _runtime_client(profile)
    cal = client["build"]("calendar", "v3", credentials=client["creds"])
    # Read-modify-write so we don't blank fields we didn't touch
    existing = cal.events().get(calendarId=calendar_id, eventId=event_id).execute()
    if summary is not None:
        existing["summary"] = summary
    if start is not None:
        existing["start"] = {"dateTime": start}
    if end is not None:
        existing["end"] = {"dateTime": end}
    if description is not None:
        existing["description"] = description
    if location is not None:
        existing["location"] = location
    cal.events().update(calendarId=calendar_id, eventId=event_id, body=existing).execute()


def delete_event(
    profile: str, event_id: str,
    *, calendar_id: str = "primary",
) -> None:
    if not is_configured(profile):
        raise RuntimeError(
            f"Google Calendar not configured for profile '{profile}'."
        )
    client = _runtime_client(profile)
    cal = client["build"]("calendar", "v3", credentials=client["creds"])
    cal.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def find_conflicts(
    profile: str,
    *,
    proposed_start: str,
    proposed_end: str,
    calendar_id: str = "primary",
) -> list[CalendarEvent]:
    """Return events that overlap with the proposed window."""
    events = list_events(
        profile,
        time_min=proposed_start,
        time_max=proposed_end,
        calendar_id=calendar_id,
    )
    # Calendar API's timeMin/timeMax already filters to overlap, but it
    # returns events that touch the window — caller decides if "touching"
    # counts as conflict (it usually does).
    return events


# ── Lazy runtime client ──────────────────────────────────────────────────


def _runtime_client(profile: str):
    try:
        from google.auth.transport.requests import Request   # type: ignore[import-not-found]
        from google.oauth2.credentials import Credentials   # type: ignore[import-not-found]
        from googleapiclient.discovery import build           # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Google API client libraries not installed. Run:\n"
            "  pip install google-api-python-client google-auth google-auth-oauthlib"
        ) from e

    token_path = credentials_path(profile)
    with open(token_path) as f:
        token_data = json.load(f)
    creds = Credentials.from_authorized_user_info(token_data, GOOGLE_CALENDAR_SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return {"creds": creds, "build": build}


def setup_interactive(profile: str, client_secret_json_path: str) -> None:
    """Run the OAuth consent flow and store the refresh token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Google OAuth library not installed. Run:\n"
            "  pip install google-auth-oauthlib"
        ) from e

    cred_dir = profile_dir(profile) / "credentials"
    cred_dir.mkdir(parents=True, exist_ok=True)
    src = Path(client_secret_json_path).expanduser()
    if not src.exists():
        raise FileNotFoundError(src)
    dest = client_secret_path(profile)
    dest.write_bytes(src.read_bytes())

    flow = InstalledAppFlow.from_client_secrets_file(str(dest), GOOGLE_CALENDAR_SCOPES)
    creds = flow.run_local_server(port=0)
    token_path = credentials_path(profile)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    print(f"✓ Stored Google Calendar token at {token_path}")


__all__ = [
    "CalendarEvent",
    "GOOGLE_CALENDAR_SCOPES",
    "credentials_path",
    "client_secret_path",
    "is_configured",
    "list_events",
    "create_event",
    "update_event",
    "delete_event",
    "find_conflicts",
    "setup_interactive",
]
