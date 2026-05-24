# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""Filesystem-based criteria: file_exists, file_contains, file_not_contains."""

from __future__ import annotations

import os
from pathlib import Path

from _framework.verifier.registry import register


@register("file_exists")
def file_exists(args: dict) -> tuple[bool, str]:
    path = args.get("path")
    if not path:
        return False, "args.path required"
    p = Path(str(path)).expanduser()
    if p.exists():
        return True, f"{p} exists"
    return False, f"{p} not found"


@register("file_contains")
def file_contains(args: dict) -> tuple[bool, str]:
    path = args.get("path")
    needle = args.get("needle")
    if not path or needle is None:
        return False, "args.path and args.needle required"
    p = Path(str(path)).expanduser()
    if not p.exists():
        return False, f"{p} not found"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"read failed: {e}"
    if needle in content:
        return True, f"{p} contains the needle"
    return False, f"{p} missing needle ({len(needle)} chars)"


@register("file_not_contains")
def file_not_contains(args: dict) -> tuple[bool, str]:
    path = args.get("path")
    needle = args.get("needle")
    if not path or needle is None:
        return False, "args.path and args.needle required"
    p = Path(str(path)).expanduser()
    if not p.exists():
        # If the file doesn't exist, the needle isn't in it. Pass.
        return True, f"{p} does not exist (vacuous pass)"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"read failed: {e}"
    if needle not in content:
        return True, f"{p} clean of needle"
    return False, f"{p} still contains forbidden needle"
