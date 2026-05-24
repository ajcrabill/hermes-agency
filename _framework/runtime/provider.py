# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Provider config resolver.

Reads `deployment.yaml::defaults` + `deployment.yaml::credentials`,
resolves credential references (env:VAR, keychain:NAME, file:PATH),
and returns a ResolvedProvider with everything the HTTP client needs
to call the inference endpoint.

The framework is vendor-neutral — this module names no vendor. It
just resolves whatever the operator put in deployment.yaml into the
shape required for a standard chat/completions HTTP call (the
common-denominator API surface across hosted and local providers).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from _framework.constants import AGENCY_HOME, DEPLOYMENT_YAML


@dataclass
class ResolvedProvider:
    """Everything needed to make an inference call."""
    name: str                           # opaque provider key from deployment.yaml
    base_url: str                       # e.g. "https://<provider-host>/v1"
    api_key: str                        # the actual key (or "" for local-no-auth)
    model: str                          # the model id (opaque string)
    timeout: int = 60                   # seconds


class ProviderResolveError(RuntimeError):
    """Raised when deployment.yaml's provider config can't be resolved."""


def resolve_default_provider() -> ResolvedProvider:
    """Load deployment.yaml and resolve the default provider config.

    Raises ProviderResolveError with a human-readable message if the
    config is missing or malformed.
    """
    import yaml

    if not DEPLOYMENT_YAML.exists():
        raise ProviderResolveError(
            f"deployment.yaml not found at {DEPLOYMENT_YAML}. "
            "Run `agency init` first."
        )

    try:
        doc = yaml.safe_load(DEPLOYMENT_YAML.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ProviderResolveError(f"deployment.yaml is not valid YAML: {e}") from e

    defaults = doc.get("defaults", {}) or {}
    creds = doc.get("credentials", {}) or {}

    provider = (defaults.get("provider") or "").strip()
    base_url = (defaults.get("base_url") or "").strip()
    model = (defaults.get("model") or "").strip()

    if not provider:
        raise ProviderResolveError(
            "deployment.yaml::defaults.provider is empty. "
            "Set it to your provider key (the same string used under "
            "`credentials:`)."
        )
    if not base_url:
        raise ProviderResolveError(
            f"deployment.yaml::defaults.base_url is empty. "
            f"Set it to the provider's chat/completions endpoint root "
            f"(e.g. '<your-provider-url>/v1' — must accept POST to /chat/completions)."
        )
    if not model:
        raise ProviderResolveError(
            f"deployment.yaml::defaults.model is empty. "
            f"Set it to the model id your provider expects."
        )

    raw_cred = creds.get(provider, "")
    if isinstance(raw_cred, str):
        raw_cred = raw_cred.strip()
    api_key = _resolve_cred_ref(raw_cred) if raw_cred else ""

    return ResolvedProvider(
        name=provider,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
    )


def _resolve_cred_ref(ref: str) -> str:
    """Turn a credential reference into the actual secret.

    Supported:
      env:VAR_NAME       → reads $VAR_NAME (looks at process env first,
                            then ~/.agency/.env)
      keychain:ENTRY     → `security find-generic-password -s ENTRY -w`
                            (macOS only)
      file:/path/to/key  → reads the file's contents (chmod 600 expected)
      env:NONE           → "" (the placeholder for local-no-auth providers)
      -                  → "" (alias for env:NONE)
    """
    if not ref or ref == "-":
        return ""

    if ref.startswith("env:"):
        var = ref[len("env:"):].strip()
        if var.upper() == "NONE":
            return ""
        # Process env wins
        val = os.environ.get(var, "")
        if val:
            return val
        # Fall back to ~/.agency/.env
        return _read_dotenv_var(var)

    if ref.startswith("keychain:"):
        entry = ref[len("keychain:"):].strip()
        try:
            r = subprocess.run(
                ["security", "find-generic-password", "-s", entry, "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return r.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        raise ProviderResolveError(
            f"Couldn't read keychain entry '{entry}'. "
            f"Check it exists: `security find-generic-password -s {entry}`"
        )

    if ref.startswith("file:"):
        path = Path(ref[len("file:"):].strip()).expanduser()
        if not path.exists():
            raise ProviderResolveError(f"credential file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    # Looks like a raw secret — refuse rather than silently use it
    raise ProviderResolveError(
        f"credential reference '{ref}' doesn't start with env: / keychain: / "
        f"file: / '-'. If you pasted a raw key into deployment.yaml, move it "
        f"into ~/.agency/.env and reference it as env:VAR_NAME instead."
    )


def _read_dotenv_var(var: str) -> str:
    """Read a single VAR from ~/.agency/.env. Returns '' if not found."""
    env_file = AGENCY_HOME / ".env"
    if not env_file.exists():
        return ""
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == var:
                v = v.strip()
                # Strip surrounding quotes
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                return v
    except OSError:
        pass
    return ""


__all__ = ["ResolvedProvider", "ProviderResolveError", "resolve_default_provider"]
