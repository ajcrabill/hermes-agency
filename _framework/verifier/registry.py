# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Verifier registry — separated to avoid circular imports.

`verifier.py` does dispatch + result modeling. `criterion_types/*` each
import `register` from here and decorate their handlers; the package
__init__ pulls them in, which triggers registration.
"""

from __future__ import annotations

from typing import Any, Callable

REGISTRY: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {}


def register(type_name: str):
    """Decorator: register a criterion handler. The handler receives the
    criterion's args dict and returns (passed, message)."""

    def deco(fn: Callable[[dict[str, Any]], tuple[bool, str]]):
        REGISTRY[type_name] = fn
        return fn

    return deco


def list_types() -> list[str]:
    return sorted(REGISTRY)


__all__ = ["REGISTRY", "register", "list_types"]
