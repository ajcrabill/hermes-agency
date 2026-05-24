# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Pricing layer — operator-registered per-(provider, model) calculators.

The framework is vendor-neutral, so it doesn't ship hardcoded prices.
Operators register a pricer for each (provider, model) they use:

  from _framework.cost.pricing import register_pricer

  register_pricer(
      provider="ollama", model="*",
      tokens_in_per_million_cents=0,    # local = free
      tokens_out_per_million_cents=0,
  )

  register_pricer(
      provider="openai-compat", model="gpt-x-fast",
      tokens_in_per_million_cents=15,   # operator looks up actual pricing
      tokens_out_per_million_cents=60,
  )

Wildcard `model="*"` matches any model under that provider.

Used by `record_inference_call` when cost_micro is not explicitly passed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pricer:
    provider: str
    model: str                        # exact model id or "*" for any
    tokens_in_per_million_cents: int   # cents per million input tokens
    tokens_out_per_million_cents: int


_PRICERS: list[Pricer] = []


def register_pricer(
    *, provider: str, model: str,
    tokens_in_per_million_cents: int = 0,
    tokens_out_per_million_cents: int = 0,
) -> None:
    """Register pricing for a (provider, model) pair. Exact-model entries
    take precedence over wildcard ("*") entries."""
    p = Pricer(
        provider=provider, model=model,
        tokens_in_per_million_cents=int(tokens_in_per_million_cents),
        tokens_out_per_million_cents=int(tokens_out_per_million_cents),
    )
    # Remove any duplicate entry for the same (provider, model)
    global _PRICERS
    _PRICERS = [x for x in _PRICERS if not (x.provider == provider and x.model == model)]
    _PRICERS.append(p)


def get_pricer(provider: str, model: str) -> Pricer | None:
    """Resolve to the most specific pricer. Exact-model wins; wildcard
    is the fallback."""
    exact = next(
        (p for p in _PRICERS if p.provider == provider and p.model == model),
        None,
    )
    if exact:
        return exact
    wildcard = next(
        (p for p in _PRICERS if p.provider == provider and p.model == "*"),
        None,
    )
    return wildcard


def compute_cost_cents(
    *, provider: str, model: str,
    tokens_in: int, tokens_out: int,
) -> float:
    """Compute the cost in cents (may be fractional). Returns 0 when no
    pricer is registered — operator hasn't told the framework yet what
    this provider costs."""
    p = get_pricer(provider, model)
    if not p:
        return 0.0
    cost = (
        tokens_in / 1_000_000 * p.tokens_in_per_million_cents
        + tokens_out / 1_000_000 * p.tokens_out_per_million_cents
    )
    return cost


def list_pricers() -> list[Pricer]:
    """For inspection; not used internally."""
    return list(_PRICERS)


def clear_pricers() -> None:
    """Mainly for tests."""
    global _PRICERS
    _PRICERS = []


__all__ = [
    "Pricer",
    "register_pricer",
    "get_pricer",
    "compute_cost_cents",
    "list_pricers",
    "clear_pricers",
]
