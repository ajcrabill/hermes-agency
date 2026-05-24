# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Slack ingress integration via Slack web API.

Operator creates a Slack app (or uses an existing one), grants the
needed scopes, installs to their workspace, and provides the bot
token. Token is stored per-profile.

Required scopes (minimum):
  - chat:write          (send messages)
  - im:history          (read DMs)
  - im:read             (list DM channels)
  - channels:history    (read public channels)
  - users:read          (resolve user IDs to names)

Setup is documented for the operator:
  1. Create Slack app at https://api.slack.com/apps
  2. Add Bot Token Scopes (above)
  3. Install to workspace
  4. Copy Bot User OAuth Token (xoxb-...)
  5. `agency integrations slack setup --profile <cos-id>
     --token xoxb-...`

Runtime use:
  from _framework.integrations.slack import (
      is_configured, poll_messages, send_message,
  )

Uses urllib so the framework doesn't depend on the slack_sdk
library — keeps the integration optional + light.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import profile_dir


SLACK_API = "https://slack.com/api"


def config_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "slack_token.json"


def is_configured(profile: str) -> bool:
    return config_path(profile).exists()


@dataclass
class SlackMessage:
    ts: str                                  # Slack ts string (used as message id)
    channel: str
    user_id: str
    user_name: str = ""
    text: str = ""
    is_dm: bool = False
    thread_ts: str | None = None
    attachments: list[dict] = field(default_factory=list)


@dataclass
class SlackConfig:
    bot_token: str
    bot_user_id: str = ""


def setup_interactive(profile: str, *, token: str) -> None:
    """Store the Slack bot token + auto-resolve the bot's user id."""
    if not token.startswith("xoxb-"):
        print("⚠ Token doesn't look like a Slack bot token (xoxb-...).")
    cred_dir = profile_dir(profile) / "credentials"
    cred_dir.mkdir(parents=True, exist_ok=True)
    # Resolve bot user id via auth.test
    bot_user_id = ""
    try:
        resp = _api_call("auth.test", token=token)
        if resp.get("ok"):
            bot_user_id = resp.get("user_id", "")
    except Exception:
        pass
    cfg = {
        "bot_token": token,
        "bot_user_id": bot_user_id,
        "configured_at": datetime.now(timezone.utc).isoformat(),
    }
    config_path(profile).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"✓ Stored Slack token at {config_path(profile)}")
    if bot_user_id:
        print(f"  Bot user id: {bot_user_id}")


def _load_config(profile: str) -> SlackConfig:
    if not is_configured(profile):
        raise RuntimeError(
            f"Slack not configured for profile '{profile}'. "
            f"Run: agency integrations slack setup --profile {profile} "
            f"--token xoxb-..."
        )
    with open(config_path(profile)) as f:
        raw = json.load(f)
    return SlackConfig(
        bot_token=raw["bot_token"],
        bot_user_id=raw.get("bot_user_id", ""),
    )


# ── API call helper ─────────────────────────────────────────────────────


def _api_call(method: str, *, token: str, **params) -> dict:
    """Call a Slack web API method. Returns the parsed JSON response.
    Raises RuntimeError on transport error."""
    url = f"{SLACK_API}/{method}"
    data = urllib.parse.urlencode(params).encode("ascii")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Slack API {method} HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
    except Exception as e:
        raise RuntimeError(f"Slack API {method} error: {e}")


# ── Public surface ─────────────────────────────────────────────────────


def poll_messages(
    profile: str, *,
    oldest_ts: str | None = None,
    limit: int = 50,
) -> list[SlackMessage]:
    """List new messages from DM channels the bot can see. For now we
    only poll DMs (private 1:1 messages); channel-level scanning is a
    separate skill.

    `oldest_ts` should be the last-seen ts from the prior poll; defaults
    to ~24h ago.
    """
    cfg = _load_config(profile)
    out: list[SlackMessage] = []
    # List DM channels
    try:
        dm_list = _api_call("conversations.list",
                              token=cfg.bot_token,
                              types="im")
    except RuntimeError:
        return out
    channels = dm_list.get("channels", [])
    for ch in channels:
        ch_id = ch.get("id")
        user_id = ch.get("user")
        if not ch_id:
            continue
        try:
            hist = _api_call("conversations.history",
                              token=cfg.bot_token,
                              channel=ch_id,
                              limit=str(limit),
                              **({"oldest": oldest_ts} if oldest_ts else {}))
        except RuntimeError:
            continue
        for msg in hist.get("messages", []):
            # Skip the bot's own messages
            if msg.get("user") == cfg.bot_user_id:
                continue
            out.append(SlackMessage(
                ts=str(msg.get("ts", "")),
                channel=ch_id,
                user_id=str(msg.get("user") or user_id),
                text=str(msg.get("text", "")),
                is_dm=True,
                thread_ts=msg.get("thread_ts"),
            ))
    return out


def send_message(
    profile: str, *,
    channel: str,
    text: str,
    thread_ts: str | None = None,
) -> bool:
    """Post a message to a Slack channel or DM. Returns True on success."""
    cfg = _load_config(profile)
    params: dict[str, str] = {"channel": channel, "text": text}
    if thread_ts:
        params["thread_ts"] = thread_ts
    try:
        resp = _api_call("chat.postMessage", token=cfg.bot_token, **params)
    except RuntimeError:
        return False
    return bool(resp.get("ok"))


def open_im(profile: str, *, user_id: str) -> str | None:
    """Open / get the DM channel id for a specific Slack user."""
    cfg = _load_config(profile)
    try:
        resp = _api_call("conversations.open",
                          token=cfg.bot_token, users=user_id)
    except RuntimeError:
        return None
    return (resp.get("channel") or {}).get("id")


__all__ = [
    "SlackMessage", "SlackConfig",
    "config_path", "is_configured",
    "setup_interactive",
    "poll_messages", "send_message", "open_im",
]
