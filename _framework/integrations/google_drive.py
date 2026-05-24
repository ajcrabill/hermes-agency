# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Google Drive integration for CoS — file upload + share.

Optional but high-value: CoS gains the ability to upload deliverables
to a shared Drive and send a share link in an outbound message,
rather than attaching files inline.

Setup:
  1. Operator creates a Google Cloud project + OAuth client (Desktop
     app type).
  2. Operator runs `agency integrations google-drive setup` which:
     - Prompts for the client_secret.json path
     - Runs the OAuth consent flow in a browser
     - Stores the resulting refresh token at:
         profiles/<cos-id>/credentials/google_drive_token.json
  3. Operator restarts CoS-side cron jobs.

Runtime use (called from CoS skills):

  from _framework.integrations.google_drive import upload_and_share
  share_url = upload_and_share(
      profile=cos_id,
      file_path="/tmp/ha/deliverables/q3-report.pdf",
      share_with=["client@example.com"],
      role="reader",
  )

The actual Google API calls live in `_runtime_client()` — guarded so
the framework boots cleanly even without `google-api-python-client`
installed. Operators install it explicitly when they want this
integration.

Token storage: profile-local. Each profile that wants Drive access
has its own token (so CoS's uploads use CoS's account, not a shared
agency account).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from _framework.constants import profile_dir


GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def credentials_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "google_drive_token.json"


def client_secret_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "google_drive_client_secret.json"


def is_configured(profile: str) -> bool:
    """True if a refresh token exists for this profile."""
    return credentials_path(profile).exists()


@dataclass
class DriveUploadResult:
    file_id: str
    name: str
    web_view_link: str
    shared_with: list[str]


def upload_and_share(
    profile: str,
    file_path: str | Path,
    *,
    share_with: list[str] | None = None,
    role: str = "reader",
    name: str | None = None,
) -> DriveUploadResult:
    """Upload a file + optionally share it. Returns the share link.

    Raises RuntimeError with actionable message if integration isn't
    configured or the Google API client lib isn't installed.
    """
    p = Path(file_path).expanduser()
    if not p.exists():
        raise FileNotFoundError(p)
    if not is_configured(profile):
        raise RuntimeError(
            f"Google Drive not configured for profile '{profile}'. "
            f"Run: agency integrations google-drive setup --profile {profile}"
        )

    client = _runtime_client(profile)   # raises if google-api-python-client missing

    file_metadata = {"name": name or p.name}
    media = client["MediaFileUpload"](str(p), resumable=True)
    drive = client["build"]("drive", "v3", credentials=client["creds"])
    uploaded = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    ).execute()

    shared_with: list[str] = []
    for addr in share_with or []:
        drive.permissions().create(
            fileId=uploaded["id"],
            body={"type": "user", "role": role, "emailAddress": addr},
            sendNotificationEmail=False,
            fields="id",
        ).execute()
        shared_with.append(addr)

    return DriveUploadResult(
        file_id=uploaded["id"],
        name=uploaded["name"],
        web_view_link=uploaded.get("webViewLink", ""),
        shared_with=shared_with,
    )


def _runtime_client(profile: str):
    """Lazy import of google libs. Raises with friendly message if absent."""
    try:
        from google.auth.transport.requests import Request   # type: ignore[import-not-found]
        from google.oauth2.credentials import Credentials   # type: ignore[import-not-found]
        from googleapiclient.discovery import build           # type: ignore[import-not-found]
        from googleapiclient.http import MediaFileUpload      # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Google API client libraries not installed. Run:\n"
            "  pip install google-api-python-client google-auth google-auth-oauthlib"
        ) from e

    token_path = credentials_path(profile)
    with open(token_path) as f:
        token_data = json.load(f)

    creds = Credentials.from_authorized_user_info(token_data, GOOGLE_DRIVE_SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        # Persist the refreshed token
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return {
        "creds": creds,
        "build": build,
        "MediaFileUpload": MediaFileUpload,
    }


# ── Setup helper (interactive — meant for `agency integrations` CLI) ────


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

    # Copy client_secret.json into profile-local location
    src = Path(client_secret_json_path).expanduser()
    if not src.exists():
        raise FileNotFoundError(src)
    dest = client_secret_path(profile)
    dest.write_bytes(src.read_bytes())

    flow = InstalledAppFlow.from_client_secrets_file(str(dest), GOOGLE_DRIVE_SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = credentials_path(profile)
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"✓ Stored refresh token at {token_path}")
    print(f"  CoS can now upload + share via _framework.integrations.google_drive.upload_and_share")


__all__ = [
    "DriveUploadResult",
    "GOOGLE_DRIVE_SCOPES",
    "credentials_path",
    "client_secret_path",
    "is_configured",
    "upload_and_share",
    "setup_interactive",
]
