# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""HTTP-based criteria: http_status."""

from __future__ import annotations

import urllib.request
import urllib.error

from _framework.verifier.registry import register


@register("http_status")
def http_status(args: dict) -> tuple[bool, str]:
    """args: { url: str, expect: int, timeout: float = 10 }"""
    url = args.get("url")
    expect = args.get("expect")
    timeout = float(args.get("timeout", 10))
    if not url or expect is None:
        return False, "args.url and args.expect required"
    try:
        with urllib.request.urlopen(str(url), timeout=timeout) as resp:
            status = resp.getcode()
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        return False, f"request failed: {e}"
    if status == int(expect):
        return True, f"GET {url} -> {status}"
    return False, f"GET {url} -> {status}, expected {expect}"
