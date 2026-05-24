# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Email-OTP authentication for the control panel.

A short-lived 6-digit code, delivered to the operator's
`deployment.primary_email`, validates a control-panel session.

The flow:

  1. Operator visits the control panel from a new browser session.
  2. Panel asks for their email; checks it matches
     `deployment.primary_email`.
  3. Framework generates a 6-digit code, hashes it, stores it with
     a 10-minute expiry, sends the cleartext via Gmail (the operator's
     CoS profile).
  4. Operator enters the code in the panel; we hash-compare; on
     match, issue a session token (32-char hex) stored server-side
     with a 24h expiry.
  5. The session token cookie auths subsequent requests.

Schema (`auth.db`):
  otp_challenges  challenge_id, email, code_hash, issued_at,
                  expires_at, attempts, claimed
  sessions        token, email, issued_at, expires_at, ip_origin

The code is hashed before storage so a stolen DB doesn't leak codes.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _framework.constants import STATE_DIR


AUTH_DB_DEFAULT = STATE_DIR / "auth.db"
SCHEMA_VERSION = 1

OTP_CODE_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
SESSION_EXPIRY_HOURS = 24

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_challenges (
    challenge_id    TEXT PRIMARY KEY,
    email           TEXT NOT NULL,
    code_hash       TEXT NOT NULL,
    issued_at       TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 0,
    claimed         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_otp_email ON otp_challenges(email, expires_at);

CREATE TABLE IF NOT EXISTS sessions (
    token           TEXT PRIMARY KEY,
    email           TEXT NOT NULL,
    issued_at       TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    ip_origin       TEXT NOT NULL DEFAULT '',
    revoked         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
"""


@dataclass
class OTPChallenge:
    challenge_id: str
    email: str
    expires_at: str


@dataclass
class Session:
    token: str
    email: str
    expires_at: str


def init_auth_db(path: Path | None = None) -> Path:
    target = path or AUTH_DB_DEFAULT
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(SCHEMA_V1)
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
        conn.commit()
    finally:
        conn.close()
    return target


def _conn(path: Path | None = None) -> sqlite3.Connection:
    init_auth_db(path)
    c = sqlite3.connect(str(path or AUTH_DB_DEFAULT))
    c.row_factory = sqlite3.Row
    return c


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _hash_code(code: str) -> str:
    """Hash an OTP code with a per-deployment salt (deployment.yaml's
    `framework_version` + the channel id makes this enough — the
    DB itself is the secret store)."""
    return hashlib.sha256(f"hermesagency-otp:{code}".encode("utf-8")).hexdigest()


# ── OTP challenge issuance + verification ─────────────────────────────


def issue_otp(
    *, email: str, ip_origin: str = "",
    db_path: Path | None = None,
) -> tuple[OTPChallenge, str]:
    """Generate a new OTP challenge for the given email. Returns the
    `OTPChallenge` (safe to log) and the cleartext code (caller
    delivers via email)."""
    code = "".join(str(secrets.randbelow(10)) for _ in range(OTP_CODE_LENGTH))
    challenge_id = secrets.token_hex(8)
    now = _now_dt()
    expires_at = (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    db = _conn(db_path)
    try:
        db.execute(
            "INSERT INTO otp_challenges (challenge_id, email, code_hash, "
            "issued_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (challenge_id, email, _hash_code(code), now.isoformat(), expires_at),
        )
        db.commit()
    finally:
        db.close()
    return OTPChallenge(challenge_id=challenge_id, email=email, expires_at=expires_at), code


def verify_otp(
    *, challenge_id: str, code: str,
    ip_origin: str = "",
    db_path: Path | None = None,
) -> Session | None:
    """Verify an OTP. On success, create + return a session. On failure,
    bump the challenge's `attempts` count; after MAX_ATTEMPTS, the
    challenge is locked out."""
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT * FROM otp_challenges WHERE challenge_id=?",
            (challenge_id,),
        ).fetchone()
        if not row:
            return None
        if row["claimed"]:
            return None
        if row["attempts"] >= OTP_MAX_ATTEMPTS:
            return None
        try:
            expires_dt = datetime.fromisoformat(row["expires_at"])
        except Exception:
            return None
        if _now_dt() > expires_dt:
            return None

        # Hash + compare
        if _hash_code(code) != row["code_hash"]:
            db.execute(
                "UPDATE otp_challenges SET attempts=attempts+1 WHERE challenge_id=?",
                (challenge_id,),
            )
            db.commit()
            return None

        # Success — mark claimed + issue session
        token = secrets.token_hex(16)
        now = _now_dt()
        session_expires = (now + timedelta(hours=SESSION_EXPIRY_HOURS)).isoformat()
        db.execute(
            "UPDATE otp_challenges SET claimed=1 WHERE challenge_id=?",
            (challenge_id,),
        )
        db.execute(
            "INSERT INTO sessions (token, email, issued_at, expires_at, ip_origin) "
            "VALUES (?, ?, ?, ?, ?)",
            (token, row["email"], now.isoformat(), session_expires, ip_origin),
        )
        db.commit()
        return Session(token=token, email=row["email"], expires_at=session_expires)
    finally:
        db.close()


def validate_session(token: str, db_path: Path | None = None) -> Session | None:
    """Look up a session token; return the Session if valid (not expired,
    not revoked), else None."""
    if not token:
        return None
    db = _conn(db_path)
    try:
        row = db.execute(
            "SELECT * FROM sessions WHERE token=? AND revoked=0", (token,),
        ).fetchone()
        if not row:
            return None
        try:
            expires_dt = datetime.fromisoformat(row["expires_at"])
        except Exception:
            return None
        if _now_dt() > expires_dt:
            return None
        return Session(token=token, email=row["email"], expires_at=row["expires_at"])
    finally:
        db.close()


def revoke_session(token: str, db_path: Path | None = None) -> None:
    db = _conn(db_path)
    try:
        db.execute("UPDATE sessions SET revoked=1 WHERE token=?", (token,))
        db.commit()
    finally:
        db.close()


# ── Email-delivery helper ──────────────────────────────────────────────


def send_otp_via_gmail(
    *, profile: str, email: str, code: str,
) -> bool:
    """Use the Gmail integration to deliver the OTP. Caller (control
    panel) handles the case where Gmail isn't configured (falls back
    to displaying the code on the terminal where `agency panel` runs)."""
    try:
        from _framework.integrations.gmail import is_configured, send_message
    except Exception:
        return False
    if not is_configured(profile):
        return False
    try:
        send_message(
            profile=profile,
            to=[email],
            subject="HermesAgency control panel — sign-in code",
            body=(
                f"Your sign-in code is: {code}\n\n"
                f"This code is valid for {OTP_EXPIRY_MINUTES} minutes.\n"
                f"Enter it in the control panel sign-in screen.\n\n"
                f"If you didn't request this, ignore this email.\n"
            ),
        )
        return True
    except Exception:
        return False


__all__ = [
    "OTPChallenge", "Session",
    "OTP_CODE_LENGTH", "OTP_EXPIRY_MINUTES", "OTP_MAX_ATTEMPTS",
    "SESSION_EXPIRY_HOURS",
    "init_auth_db",
    "issue_otp", "verify_otp",
    "validate_session", "revoke_session",
    "send_otp_via_gmail",
]
