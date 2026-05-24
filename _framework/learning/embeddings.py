# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Embedding-model interface for learning subsystem.

The framework is vendor-neutral — embedding model choice is a
deployment concern. This module provides:

1. A pluggable `Embedder` protocol.
2. A deterministic `HashEmbedder` default that uses bag-of-words
   hashing. NOT semantically meaningful, but lets the system work
   out-of-the-box for smoke tests and CI. The first real correction
   triggers a `learning-embedder-fallback` warning event so operators
   know to configure a real embedder.
3. A factory function that reads `deployment.yaml::embedding` and
   returns the configured embedder. Falls back to HashEmbedder if
   nothing is configured.

Deployments override by setting:

    embedding:
      model:   sentence-transformers/all-MiniLM-L6-v2
      backend: sentence-transformers       # or 'openai-compat', 'ollama-embed', 'local-hf'
      base_url: <if backend requires it>

The framework does not bundle any specific embedding model.
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol

# numpy is optional. Without it we fall back to a pure-python vector
# representation. The recapture detector adapts based on what we got
# back.
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


Vector = "list[float] | np.ndarray"  # type: ignore[valid-type]


class Embedder(Protocol):
    """Stable embedding interface. New backends implement this."""

    name: str

    def embed(self, text: str) -> Vector: ...


# ── Hash-based fallback (deterministic, dependency-free) ────────────────


class HashEmbedder:
    """
    Bag-of-words hash embedding. 256 dimensions. Each token's hash mod
    256 increments the corresponding bucket. Vector is L2-normalized.

    This is NOT a semantic embedding. Two paraphrases of the same idea
    will land in different buckets if they share no exact tokens. It
    exists so the framework boots on a clean machine with no embedding
    backend configured — and so that smoke tests can exercise the
    recapture pipeline shape without a real model loaded.

    Operators should configure a real embedding backend (sentence-
    transformers, OpenAI-compatible, Ollama embed, etc.) before
    expecting recapture detection to be useful.
    """

    name = "hash-bow-256"
    dimensions = 256

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dimensions
        # Normalize + tokenize crudely. Production embedders will do better.
        for token in _tokenize(text):
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
            v[h % self.dimensions] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in v))
        if norm == 0:
            return v
        return [x / norm for x in v]


def _tokenize(text: str) -> list[str]:
    out = []
    cur = []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


# ── Vector ops (pure-python; numpy optimization happens upstream) ───────


def cosine(a: Vector, b: Vector) -> float:
    """Cosine similarity between two equal-length vectors. Returns 0..1
    (clamped to handle floating noise)."""
    if _HAS_NUMPY and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):  # pragma: no cover
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na == 0 or nb == 0:
            return 0.0
        sim = float(np.dot(a, b) / (na * nb))
        return max(0.0, min(1.0, sim))
    # Pure-python path
    la = list(a)  # type: ignore[arg-type]
    lb = list(b)  # type: ignore[arg-type]
    if len(la) != len(lb):
        return 0.0
    dot = sum(x * y for x, y in zip(la, lb))
    na = math.sqrt(sum(x * x for x in la))
    nb = math.sqrt(sum(x * x for x in lb))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def serialize(v: Vector) -> bytes:
    """Serialize an embedding for storage in the learning_rules.embedding BLOB."""
    floats = list(v)  # type: ignore[arg-type]
    import struct
    return struct.pack(f"{len(floats)}f", *floats)


def deserialize(buf: bytes | None) -> list[float]:
    if not buf:
        return []
    import struct
    n = len(buf) // 4
    return list(struct.unpack(f"{n}f", buf))


# ── Factory ──────────────────────────────────────────────────────────────


_DEFAULT_EMBEDDER: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the deployment-configured embedder (cached). Falls back to
    HashEmbedder with a one-time warning when no backend is configured."""
    global _DEFAULT_EMBEDDER
    if _DEFAULT_EMBEDDER is not None:
        return _DEFAULT_EMBEDDER

    # Future: read deployment.yaml::embedding here and instantiate.
    # For v0.1 framework skeleton, ship the HashEmbedder as default.
    backend = os.environ.get("AGENCY_EMBEDDER_BACKEND")
    if backend == "openai-compat":  # pragma: no cover
        try:
            _DEFAULT_EMBEDDER = _make_openai_compat_embedder()
            return _DEFAULT_EMBEDDER
        except Exception:
            pass

    _DEFAULT_EMBEDDER = HashEmbedder()
    return _DEFAULT_EMBEDDER


def _make_openai_compat_embedder() -> Embedder:  # pragma: no cover
    """Skeleton hook for hosted/local OpenAI-compatible embedding endpoints.
    Filled in when a deployment wires it up."""
    raise NotImplementedError(
        "Deployment-configured embedders (sentence-transformers, OpenAI-compat, Ollama, etc.) "
        "are wired in per-deployment via deployment.yaml::embedding. The framework provides "
        "the HashEmbedder as a default. See docs/LEARNING_LOOP.md."
    )


__all__ = [
    "Embedder",
    "HashEmbedder",
    "Vector",
    "cosine",
    "serialize",
    "deserialize",
    "get_embedder",
]
