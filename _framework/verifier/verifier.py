# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Verifier core — registry + execution.

The actual checkers live in `criterion_types/`. This file is the
dispatcher: given a list of `{type, args}` dicts, run each against the
registered handler and collect results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .registry import REGISTRY, register, list_types
# Importing criterion_types triggers each submodule's @register() calls.
# Kept at the bottom-of-module import position via lazy access in Verifier.run.
from . import criterion_types as _criterion_types  # noqa: F401


# ── Result objects ──────────────────────────────────────────────────────


@dataclass
class CriterionFailure:
    type: str
    args: dict[str, Any]
    message: str


@dataclass
class VerificationResult:
    passed: bool
    n_criteria: int
    failures: list[CriterionFailure] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1


# ── Verifier ────────────────────────────────────────────────────────────


class Verifier:
    """Stateless; thin wrapper for the registry lookup + execution."""

    @staticmethod
    def run(criteria: list[dict[str, Any]]) -> VerificationResult:
        if not criteria:
            # fail-closed: no criteria → cannot verify
            return VerificationResult(
                passed=False,
                n_criteria=0,
                failures=[CriterionFailure(
                    type="<none>", args={},
                    message="No verifier criteria declared. Completion refused (fail-closed).",
                )],
            )
        failures: list[CriterionFailure] = []
        notes: list[str] = []
        for crit in criteria:
            t = crit.get("type")
            args = crit.get("args", {})
            if t not in REGISTRY:
                failures.append(CriterionFailure(
                    type=str(t), args=args,
                    message=f"unknown criterion type '{t}' — register one in _framework/verifier/criterion_types/.",
                ))
                continue
            try:
                passed, msg = REGISTRY[t](args)
            except Exception as e:  # pragma: no cover
                passed, msg = False, f"handler raised: {type(e).__name__}: {e}"
            if not passed:
                failures.append(CriterionFailure(type=str(t), args=args, message=msg))
            else:
                notes.append(f"{t}: ✓ {msg}")
        return VerificationResult(
            passed=not failures,
            n_criteria=len(criteria),
            failures=failures,
            notes=notes,
        )


def check(criteria: list[dict[str, Any]]) -> VerificationResult:
    """Module-level convenience."""
    return Verifier.run(criteria)


__all__ = ["Verifier", "VerificationResult", "CriterionFailure", "register", "check", "list_types", "REGISTRY"]
# noqa-named exports — `register`, `list_types`, `REGISTRY` come from .registry above.
