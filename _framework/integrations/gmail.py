# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Gmail API integration — list / get / send / modify / draft.

Same pattern as `google_drive` and `google_calendar`: lazy-imported
runtime client, profile-local OAuth credentials, optional Python
deps. The framework boots without `google-api-python-client`; the
integration becomes available when the operator installs the libs
+ runs setup.

Setup:
  agency integrations gmail setup \\
      --profile <cos-id> \\
      --client-secret /path/to/client_secret.json

Token storage: `profiles/<cos-id>/credentials/gmail_token.json`.

Runtime use (typical CoS callers):

  from _framework.integrations.gmail import (
      list_new_messages, get_message, send_message, modify_labels,
  )

  for msg in list_new_messages(profile=cos_id, query="is:unread"):
      ...

  send_message(profile=cos_id,
               to=["client@example.com"], subject="...", body="...")

Scopes (each operator opts into the minimum needed):

  - gmail.readonly  → list + get
  - gmail.send      → send_message + create_draft
  - gmail.modify    → modify_labels (archive/star/etc.) + send
                      (modify is a superset including send)

The default setup requests `gmail.modify` because most agency
workflows need both inbox reading + sending. Operators who want
read-only access pass `--scopes readonly` at setup.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Iterable

from _framework.constants import profile_dir


GMAIL_SCOPE_PRESETS = {
    "readonly": ["https://www.googleapis.com/auth/gmail.readonly"],
    "send": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ],
    "modify": ["https://www.googleapis.com/auth/gmail.modify"],   # superset
}
DEFAULT_SCOPES = GMAIL_SCOPE_PRESETS["modify"]


def credentials_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "gmail_token.json"


def client_secret_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "gmail_client_secret.json"


def is_configured(profile: str) -> bool:
    return credentials_path(profile).exists()


# ── Data types ──────────────────────────────────────────────────────────


@dataclass
class GmailMessage:
    id: str
    thread_id: str
    label_ids: list[str] = field(default_factory=list)
    snippet: str = ""
    from_addr: str = ""
    from_name: str = ""
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    subject: str = ""
    date: str = ""
    body_text: str = ""
    body_html: str = ""
    has_attachments: bool = False


@dataclass
class SendResult:
    id: str
    thread_id: str
    label_ids: list[str] = field(default_factory=list)


# ── List + get ──────────────────────────────────────────────────────────


def list_new_messages(
    profile: str,
    *,
    query: str = "is:unread",
    max_results: int = 50,
) -> list[GmailMessage]:
    """List messages matching a Gmail search query (e.g. `is:unread`,
    `from:client@x.com`, `newer_than:1d`). Returns hydrated GmailMessage
    objects (one round-trip per message — for large batches, call
    `list_message_ids` first and `get_message` selectively)."""
    ids = list_message_ids(profile=profile, query=query, max_results=max_results)
    return [get_message(profile=profile, message_id=mid) for mid in ids]


def list_message_ids(
    profile: str,
    *,
    query: str = "is:unread",
    max_results: int = 100,
) -> list[str]:
    """Return just the message ids for a query. Cheap; ~1 API call."""
    _require_configured(profile)
    client = _runtime_client(profile)
    svc = client["build"]("gmail", "v1", credentials=client["creds"])
    resp = svc.users().messages().list(
        userId="me", q=query, maxResults=max_results,
    ).execute()
    return [m["id"] for m in resp.get("messages", [])]


def get_message(profile: str, message_id: str) -> GmailMessage:
    """Fetch full message + parse headers/body."""
    _require_configured(profile)
    client = _runtime_client(profile)
    svc = client["build"]("gmail", "v1", credentials=client["creds"])
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full",
    ).execute()

    headers = {h["name"].lower(): h["value"]
               for h in msg.get("payload", {}).get("headers", [])}

    out = GmailMessage(
        id=msg.get("id", ""),
        thread_id=msg.get("threadId", ""),
        label_ids=msg.get("labelIds", []),
        snippet=msg.get("snippet", ""),
        subject=headers.get("subject", ""),
        date=headers.get("date", ""),
    )
    from_raw = headers.get("from", "")
    out.from_name, out.from_addr = _parse_addr(from_raw)
    out.to = [_parse_addr(x)[1] for x in headers.get("to", "").split(",") if x.strip()]
    out.cc = [_parse_addr(x)[1] for x in headers.get("cc", "").split(",") if x.strip()]

    # Walk payload parts for text + html bodies
    text, html, has_att = _extract_bodies(msg.get("payload", {}))
    out.body_text = text
    out.body_html = html
    out.has_attachments = has_att
    return out


def _extract_bodies(payload: dict) -> tuple[str, str, bool]:
    """Walk the MIME tree. Return (text, html, has_attachments)."""
    text = ""
    html = ""
    has_att = False

    def walk(part: dict) -> None:
        nonlocal text, html, has_att
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        if body.get("attachmentId"):
            has_att = True
        data = body.get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data + "==").decode(
                    "utf-8", errors="replace",
                )
            except Exception:
                decoded = ""
            if mime == "text/plain" and not text:
                text = decoded
            elif mime == "text/html" and not html:
                html = decoded
        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    return text, html, has_att


# ── Send + draft ────────────────────────────────────────────────────────


def send_message(
    profile: str,
    *,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    body_html: str | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
    thread_id: str | None = None,
    attachments: list[Path] | None = None,
) -> SendResult:
    """Send a message. `in_reply_to` + `references` allow threading
    into an existing conversation; `thread_id` pins to Gmail's own
    thread identifier (preferred when both are available)."""
    _require_configured(profile)
    client = _runtime_client(profile)
    svc = client["build"]("gmail", "v1", credentials=client["creds"])

    mime = _build_mime(
        to=to, cc=cc or [], bcc=bcc or [],
        subject=subject, body_text=body, body_html=body_html,
        in_reply_to=in_reply_to,
        references=references or ([in_reply_to] if in_reply_to else []),
        attachments=attachments or [],
    )
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")

    body_payload: dict = {"raw": raw}
    if thread_id:
        body_payload["threadId"] = thread_id

    resp = svc.users().messages().send(userId="me", body=body_payload).execute()
    return SendResult(
        id=resp.get("id", ""),
        thread_id=resp.get("threadId", ""),
        label_ids=resp.get("labelIds", []),
    )


def create_draft(
    profile: str,
    *,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    body_html: str | None = None,
    in_reply_to: str | None = None,
    thread_id: str | None = None,
) -> str:
    """Create a Gmail draft (visible in operator's Gmail web UI as a
    pending draft). Returns draft id."""
    _require_configured(profile)
    client = _runtime_client(profile)
    svc = client["build"]("gmail", "v1", credentials=client["creds"])

    mime = _build_mime(
        to=to, cc=cc or [], bcc=bcc or [],
        subject=subject, body_text=body, body_html=body_html,
        in_reply_to=in_reply_to,
        references=[in_reply_to] if in_reply_to else [],
        attachments=[],
    )
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")

    msg_payload = {"raw": raw}
    if thread_id:
        msg_payload["threadId"] = thread_id
    resp = svc.users().drafts().create(
        userId="me", body={"message": msg_payload},
    ).execute()
    return resp.get("id", "")


# ── Label modification (archive / star / mark read) ─────────────────────


def modify_labels(
    profile: str,
    *,
    message_id: str,
    add: Iterable[str] = (),
    remove: Iterable[str] = (),
) -> None:
    """Add / remove labels on a message. Gmail uses labels for
    archive (remove `INBOX`), star (add `STARRED`), unread/read
    (add/remove `UNREAD`)."""
    _require_configured(profile)
    client = _runtime_client(profile)
    svc = client["build"]("gmail", "v1", credentials=client["creds"])
    svc.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": list(add), "removeLabelIds": list(remove)},
    ).execute()


def archive_message(profile: str, message_id: str) -> None:
    """Convenience: remove INBOX label (Gmail's archive)."""
    modify_labels(profile, message_id=message_id, remove=["INBOX"])


def mark_read(profile: str, message_id: str) -> None:
    modify_labels(profile, message_id=message_id, remove=["UNREAD"])


# ── MIME builder ────────────────────────────────────────────────────────


def _build_mime(
    *,
    to: list[str], cc: list[str], bcc: list[str],
    subject: str, body_text: str, body_html: str | None,
    in_reply_to: str | None, references: list[str],
    attachments: list[Path],
) -> MIMEMultipart | MIMEText:
    """Build a MIME message. If attachments present, multipart/mixed;
    if both text + html, multipart/alternative inside; else simple text."""
    has_attachments = bool(attachments)
    has_html = body_html is not None

    if has_attachments:
        outer = MIMEMultipart("mixed")
        if has_html:
            body_part = MIMEMultipart("alternative")
            body_part.attach(MIMEText(body_text, "plain", "utf-8"))
            body_part.attach(MIMEText(body_html or "", "html", "utf-8"))
            outer.attach(body_part)
        else:
            outer.attach(MIMEText(body_text, "plain", "utf-8"))
        for att in attachments:
            outer.attach(_mime_attachment(att))
        msg = outer
    elif has_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html or "", "html", "utf-8"))
    else:
        msg = MIMEText(body_text, "plain", "utf-8")

    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(r for r in references if r)
    return msg


def _mime_attachment(path: Path) -> MIMEBase:
    with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
    return part


# ── Helpers ─────────────────────────────────────────────────────────────


def _parse_addr(raw: str) -> tuple[str, str]:
    """Return (display_name, email) from a 'Name <email@x.com>' header.
    Falls back to ('', raw) if no name is present."""
    raw = raw.strip()
    if "<" in raw and ">" in raw:
        name = raw.split("<")[0].strip().strip('"')
        addr = raw.split("<", 1)[1].rstrip(">").strip()
        return name, addr
    return "", raw


def _require_configured(profile: str) -> None:
    if not is_configured(profile):
        raise RuntimeError(
            f"Gmail not configured for profile '{profile}'. "
            f"Run: agency integrations gmail setup --profile {profile} "
            f"--client-secret /path/to/client_secret.json"
        )


# ── Runtime client + interactive setup ──────────────────────────────────


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
    creds = Credentials.from_authorized_user_info(token_data, DEFAULT_SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return {"creds": creds, "build": build}


def setup_interactive(
    profile: str, client_secret_json_path: str,
    *, scope_preset: str = "modify",
) -> None:
    """Run the OAuth consent flow + store the refresh token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow   # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Google OAuth library not installed. Run:\n"
            "  pip install google-auth-oauthlib"
        ) from e

    if scope_preset not in GMAIL_SCOPE_PRESETS:
        raise ValueError(
            f"unknown scope preset {scope_preset!r}; "
            f"choose from {list(GMAIL_SCOPE_PRESETS)}"
        )
    scopes = GMAIL_SCOPE_PRESETS[scope_preset]

    cred_dir = profile_dir(profile) / "credentials"
    cred_dir.mkdir(parents=True, exist_ok=True)
    src = Path(client_secret_json_path).expanduser()
    if not src.exists():
        raise FileNotFoundError(src)
    dest = client_secret_path(profile)
    dest.write_bytes(src.read_bytes())

    flow = InstalledAppFlow.from_client_secrets_file(str(dest), scopes)
    creds = flow.run_local_server(port=0)
    token_path = credentials_path(profile)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    print(f"✓ Stored Gmail token at {token_path}")
    print(f"  Scopes: {', '.join(scopes)}")


__all__ = [
    "GMAIL_SCOPE_PRESETS",
    "GmailMessage", "SendResult",
    "credentials_path", "client_secret_path", "is_configured",
    "list_new_messages", "list_message_ids", "get_message",
    "send_message", "create_draft",
    "modify_labels", "archive_message", "mark_read",
    "setup_interactive",
]
