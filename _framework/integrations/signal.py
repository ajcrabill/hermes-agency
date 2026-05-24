# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Signal ingress integration via signal-cli.

Signal doesn't expose a hosted API; the operator runs `signal-cli`
locally (registered with their own Signal account or a dedicated
agency Signal number). HermesAgency invokes signal-cli as a
subprocess to poll for new messages + send replies.

Setup is documented for the operator, not automated:
  1. Install signal-cli (e.g. brew install signal-cli)
  2. Register a number with signal-cli (one-time)
  3. Verify with the SMS / call code Signal sends
  4. Run `agency integrations signal setup --profile <cos-id>
     --signal-number +15551234567` to record the configuration
     in the profile credentials dir.

Runtime use (CoS owner-channels-ingress polls Signal alongside email):

  from _framework.integrations.signal import (
      is_configured, poll_messages, send_message,
  )

The framework doesn't bundle signal-cli. It calls it via subprocess
+ JSON-RPC mode (the recommended invocation for programmatic use).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from _framework.constants import profile_dir


def config_path(profile: str) -> Path:
    return profile_dir(profile) / "credentials" / "signal_config.json"


def is_configured(profile: str) -> bool:
    return config_path(profile).exists()


def signal_cli_available() -> bool:
    """True if signal-cli is on PATH."""
    return shutil.which("signal-cli") is not None


@dataclass
class SignalMessage:
    timestamp: int                    # signal's millisecond timestamp
    from_number: str
    from_name: str = ""
    body: str = ""
    attachments: list[str] = field(default_factory=list)
    group_id: str | None = None


@dataclass
class SignalConfig:
    """Per-profile signal configuration."""

    signal_number: str
    signal_cli_path: str = ""           # explicit override; "" means use PATH


def setup_interactive(profile: str, *, signal_number: str) -> None:
    """Record the signal config for a profile. Doesn't register the
    number with Signal itself — that's `signal-cli register` + verify,
    which the operator runs separately."""
    cred_dir = profile_dir(profile) / "credentials"
    cred_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "signal_number": signal_number,
        "configured_at": datetime.now(timezone.utc).isoformat(),
    }
    config_path(profile).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"✓ Recorded Signal config at {config_path(profile)}")
    if not signal_cli_available():
        print("  ⚠ signal-cli not on PATH. Install + register your number:")
        print("    https://github.com/AsamK/signal-cli")
    else:
        print(f"  signal-cli detected at: {shutil.which('signal-cli')}")


def _load_config(profile: str) -> SignalConfig:
    if not is_configured(profile):
        raise RuntimeError(
            f"Signal not configured for profile '{profile}'. "
            f"Run: agency integrations signal setup --profile {profile} "
            f"--signal-number +1234567890"
        )
    with open(config_path(profile)) as f:
        raw = json.load(f)
    return SignalConfig(
        signal_number=raw["signal_number"],
        signal_cli_path=raw.get("signal_cli_path", ""),
    )


def _signal_cli_bin(cfg: SignalConfig) -> str:
    return cfg.signal_cli_path or "signal-cli"


def poll_messages(profile: str, timeout: int = 10) -> list[SignalMessage]:
    """Receive any new messages. Returns parsed SignalMessage objects.

    signal-cli's `receive` blocks for `timeout` seconds; we parse its
    JSON output. Empty list = no new messages this poll.
    """
    cfg = _load_config(profile)
    if not signal_cli_available() and not cfg.signal_cli_path:
        raise RuntimeError(
            "signal-cli not on PATH. Install it (https://github.com/AsamK/signal-cli) "
            "or set signal_cli_path in the profile config."
        )
    cmd = [
        _signal_cli_bin(cfg),
        "-a", cfg.signal_number,
        "-o", "json",
        "receive",
        "-t", str(timeout),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return []
    if proc.returncode != 0:
        return []
    messages: list[SignalMessage] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            envelope = json.loads(line).get("envelope", {})
        except json.JSONDecodeError:
            continue
        data_msg = envelope.get("dataMessage")
        if not data_msg:
            continue
        attachments = []
        for a in data_msg.get("attachments", []) or []:
            ident = a.get("id") or a.get("filename")
            if ident:
                attachments.append(str(ident))
        messages.append(SignalMessage(
            timestamp=int(envelope.get("timestamp", 0)),
            from_number=str(envelope.get("source", "")),
            from_name=str(envelope.get("sourceName", "")),
            body=str(data_msg.get("message") or ""),
            attachments=attachments,
            group_id=(data_msg.get("groupInfo") or {}).get("groupId"),
        ))
    return messages


def send_message(
    profile: str, *,
    to_number: str | None = None,
    group_id: str | None = None,
    body: str,
    attachments: list[Path] | None = None,
) -> bool:
    """Send a Signal message to a direct number or a group. Returns
    True on success."""
    cfg = _load_config(profile)
    if not (to_number or group_id):
        raise ValueError("must specify to_number or group_id")
    cmd = [_signal_cli_bin(cfg), "-a", cfg.signal_number, "send"]
    if group_id:
        cmd.extend(["-g", group_id])
    if to_number:
        cmd.append(to_number)
    cmd.extend(["-m", body])
    for att in attachments or []:
        cmd.extend(["-a", str(att)])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        return False


__all__ = [
    "SignalMessage", "SignalConfig",
    "config_path", "is_configured", "signal_cli_available",
    "setup_interactive",
    "poll_messages", "send_message",
]
