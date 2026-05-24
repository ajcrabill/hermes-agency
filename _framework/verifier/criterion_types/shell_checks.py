# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""Shell-based criteria: shell_exit_zero.

USE SPARINGLY. Shell-based checks are arbitrary code execution at
verifier time. Prefer typed criteria (sql_query, file_exists, etc.)
whenever possible. This exists for the cases where there's no other
way to assert a real-world side effect.
"""

from __future__ import annotations

import shlex
import subprocess

from _framework.verifier.registry import register


@register("shell_exit_zero")
def shell_exit_zero(args: dict) -> tuple[bool, str]:
    """args: { command: str, timeout: int = 30 }

    Runs the command and asserts exit-code 0. Returns the last 200 chars
    of stdout/stderr on failure for diagnosis.
    """
    cmd = args.get("command")
    timeout = int(args.get("timeout", 30))
    if not cmd:
        return False, "args.command required"
    try:
        proc = subprocess.run(
            cmd if isinstance(cmd, list) else shlex.split(str(cmd)),
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {timeout}s"
    except FileNotFoundError as e:
        return False, f"command not found: {e}"
    if proc.returncode == 0:
        return True, "exit 0"
    out = (proc.stdout + proc.stderr)[-200:]
    return False, f"exit {proc.returncode}: {out}"
