# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Example ingestion — take whatever the operator sends (URL, file path,
raw text, or a kanban task body) and return normalized text.

The framework's job here is the boring part: normalize. Style
analysis is in `style.py`; iteration tracking in `iteration.py`.

Supported sources:
  - HTTP/HTTPS URL → fetch + extract text (uses readability heuristics)
  - Local file path → format-aware extraction (.txt, .md, .docx, .pdf)
  - Raw string → pass-through

The HTTP fetcher is intentionally simple — it uses urllib and a
crude tag-stripper. Operators who need a heavier extractor (full
readability lib, JS rendering, paywall handling) can swap the
backend by passing a custom `fetcher` callable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import urllib.error
import urllib.request


@dataclass
class IngestResult:
    """One example after normalization."""

    source: str          # the original URL / path / "<raw>"
    text: str            # extracted/normalized text
    format: str          # "html" | "text" | "docx" | "pdf" | "raw" | "error:<reason>"
    chars: int
    metadata: dict       # source-specific (e.g. {"http_status": 200, "content_type": "..."})


# ── Per-format extractors ────────────────────────────────────────────────


def _ingest_http(url: str, timeout: float = 15.0) -> IngestResult:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "HermesAgency/example-ingest"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
    except urllib.error.HTTPError as e:
        return IngestResult(source=url, text="", format=f"error:http-{e.code}",
                            chars=0, metadata={"http_status": e.code})
    except Exception as e:
        return IngestResult(source=url, text="", format=f"error:{type(e).__name__}",
                            chars=0, metadata={"reason": str(e)})

    # Decode (best-effort)
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)

    if "html" in content_type.lower():
        text = _strip_html(text)
        fmt = "html"
    elif "text/" in content_type.lower() or "markdown" in content_type.lower():
        fmt = "text"
    else:
        fmt = "html" if "<html" in text[:1000].lower() else "text"
        if fmt == "html":
            text = _strip_html(text)

    text = _normalize_whitespace(text)
    return IngestResult(
        source=url, text=text, format=fmt, chars=len(text),
        metadata={"http_status": 200, "content_type": content_type},
    )


def _ingest_file(path: Path) -> IngestResult:
    suffix = path.suffix.lower()
    try:
        if suffix in (".txt", ".md", ".markdown"):
            text = path.read_text(encoding="utf-8", errors="replace")
            return IngestResult(source=str(path), text=_normalize_whitespace(text),
                                 format="text", chars=len(text),
                                 metadata={"suffix": suffix})
        if suffix == ".docx":
            try:
                import docx2txt   # type: ignore[import-not-found]
                text = docx2txt.process(str(path)) or ""
                text = _normalize_whitespace(text)
                return IngestResult(source=str(path), text=text, format="docx",
                                     chars=len(text), metadata={"suffix": suffix})
            except ImportError:
                return IngestResult(source=str(path), text="",
                                     format="error:docx-missing-extractor",
                                     chars=0, metadata={
                                         "remediation": "pip install docx2txt"
                                     })
        if suffix == ".pdf":
            import shutil, subprocess
            if shutil.which("pdftotext"):
                out = subprocess.run(["pdftotext", str(path), "-"],
                                      capture_output=True, text=True, timeout=60)
                if out.returncode == 0:
                    text = _normalize_whitespace(out.stdout)
                    return IngestResult(source=str(path), text=text, format="pdf",
                                         chars=len(text), metadata={"suffix": suffix})
            try:
                import pdfplumber   # type: ignore[import-not-found]
                with pdfplumber.open(str(path)) as pdf:
                    text = "\n\n".join(p.extract_text() or "" for p in pdf.pages)
                text = _normalize_whitespace(text)
                return IngestResult(source=str(path), text=text, format="pdf",
                                     chars=len(text), metadata={"suffix": suffix})
            except ImportError:
                return IngestResult(source=str(path), text="",
                                     format="error:pdf-missing-extractor",
                                     chars=0, metadata={
                                         "remediation": "pip install pdfplumber or brew install poppler"
                                     })
        return IngestResult(source=str(path), text="",
                             format=f"error:unsupported-format:{suffix}",
                             chars=0, metadata={"suffix": suffix})
    except Exception as e:
        return IngestResult(source=str(path), text="",
                             format=f"error:{type(e).__name__}",
                             chars=0, metadata={"reason": str(e)})


def _ingest_raw(text: str) -> IngestResult:
    text = _normalize_whitespace(text)
    return IngestResult(source="<raw>", text=text, format="raw",
                         chars=len(text), metadata={})


# ── Public API ──────────────────────────────────────────────────────────


def ingest_example(
    source: str,
    *,
    fetcher: Callable[[str], IngestResult] | None = None,
) -> IngestResult:
    """Ingest a single example. `source` is auto-detected:
      - "http://..." or "https://..." → fetched via urllib
      - existing file path → format-aware extraction
      - anything else → treated as raw text
    `fetcher` overrides the HTTP path (tests pass a stub)."""
    if not source:
        return IngestResult(source="", text="", format="error:empty-source",
                             chars=0, metadata={})
    if source.startswith("http://") or source.startswith("https://"):
        return (fetcher or _ingest_http)(source)
    p = Path(source).expanduser()
    if p.exists() and p.is_file():
        return _ingest_file(p)
    return _ingest_raw(source)


def ingest_examples(
    sources: list[str],
    *,
    fetcher: Callable[[str], IngestResult] | None = None,
) -> list[IngestResult]:
    """Ingest a batch. Maintains order. Each result is independent;
    one failure doesn't poison the others."""
    return [ingest_example(s, fetcher=fetcher) for s in sources]


# ── Helpers ─────────────────────────────────────────────────────────────


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_HTML_ENTITY_RE = re.compile(r"&(?:[a-zA-Z]+|#\d+);")
_HTML_ENTITIES = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#39;": "'", "&apos;": "'",
}
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n\s*\n\s*\n+")


def _strip_html(html: str) -> str:
    # Drop script + style entirely
    text = _HTML_SCRIPT_RE.sub(" ", html)
    text = _HTML_TAG_RE.sub(" ", text)
    # Decode the common entities
    for ent, rep in _HTML_ENTITIES.items():
        text = text.replace(ent, rep)
    text = _HTML_ENTITY_RE.sub(" ", text)
    return _normalize_whitespace(text)


def _normalize_whitespace(text: str) -> str:
    # Collapse runs of spaces/tabs, collapse 3+ blank lines into 2
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


__all__ = ["IngestResult", "ingest_example", "ingest_examples"]
