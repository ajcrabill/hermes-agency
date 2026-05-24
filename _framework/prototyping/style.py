# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Style derivation — analyze normalized text to produce a style
signature the prompt can carry forward when drafting the prototype.

This is intentionally a *coarse* analysis: rhythm, length distribution,
register markers, structural patterns. The fine work (does this draft
*sound* like the examples?) belongs to the LLM at draft time, given
the signature as context. Our job is to give the LLM a structured
characterization of the examples rather than just dumping the raw
text in.

The signature is deterministic + JSON-serializable so prototype DB
rounds can persist it across iterations.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import asdict, dataclass, field
from typing import Iterable


@dataclass
class StyleSignature:
    """Structured characterization of one or more example texts."""

    n_examples: int
    total_chars: int
    avg_sentence_chars: float
    median_sentence_chars: float
    p90_sentence_chars: int             # 90th percentile sentence length
    paragraph_density: float            # avg paragraph length in chars
    short_sentence_pct: float           # % of sentences ≤ 80 chars
    long_sentence_pct: float            # % of sentences ≥ 200 chars
    register: list[str]                 # ['conversational', 'analytical', 'formal', ...]
    structural_signals: list[str]       # ['uses_headings', 'numbered_lists', 'bullet_lists', 'quotes_others', ...]
    distinctive_phrases: list[str]      # top recurring 2-4 word phrases
    formatting_notes: list[str]         # operator-facing observations
    summary: str = ""                   # one-paragraph human summary

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt_block(self) -> str:
        """Render as a markdown block to inject into a drafting prompt."""
        lines = [
            "## Style signature (derived from examples)",
            "",
            self.summary,
            "",
            f"- Avg sentence: ~{self.avg_sentence_chars:.0f} chars  "
            f"(p50: {self.median_sentence_chars:.0f}, p90: {self.p90_sentence_chars})",
            f"- Paragraph density: ~{self.paragraph_density:.0f} chars",
            f"- Short sentences (≤80 chars): {self.short_sentence_pct:.0%}",
            f"- Long sentences (≥200 chars): {self.long_sentence_pct:.0%}",
        ]
        if self.register:
            lines.append(f"- Register: {', '.join(self.register)}")
        if self.structural_signals:
            lines.append(f"- Structural signals: {', '.join(self.structural_signals)}")
        if self.distinctive_phrases:
            top = ", ".join(f"`{p}`" for p in self.distinctive_phrases[:8])
            lines.append(f"- Distinctive phrases: {top}")
        if self.formatting_notes:
            lines.append("")
            lines.append("**Formatting notes:**")
            for n in self.formatting_notes:
                lines.append(f"- {n}")
        return "\n".join(lines)


# ── Derivation ──────────────────────────────────────────────────────────


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])[\s\n]+(?=[A-Z\"'(])")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.M)
_NUMBERED_LIST_RE = re.compile(r"^\s*\d+\.\s+\S", re.M)
_BULLET_LIST_RE = re.compile(r"^\s*[-*+]\s+\S", re.M)
_QUOTE_LINE_RE = re.compile(r"^\s*>\s+\S", re.M)
_CODE_FENCE_RE = re.compile(r"^```", re.M)


def derive_style(texts: Iterable[str]) -> StyleSignature:
    """Analyze one or more example texts and return a structured signature."""
    text_list = [t for t in texts if t and t.strip()]
    if not text_list:
        return StyleSignature(
            n_examples=0, total_chars=0,
            avg_sentence_chars=0.0, median_sentence_chars=0.0,
            p90_sentence_chars=0, paragraph_density=0.0,
            short_sentence_pct=0.0, long_sentence_pct=0.0,
            register=[], structural_signals=[],
            distinctive_phrases=[], formatting_notes=[],
            summary="(no examples — nothing to derive)",
        )

    full = "\n\n".join(text_list)
    total_chars = len(full)

    # Sentence stats
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(full) if s.strip()]
    if sentences:
        lens = [len(s) for s in sentences]
        avg_s = sum(lens) / len(lens)
        med_s = statistics.median(lens)
        srt = sorted(lens)
        p90 = srt[max(0, int(len(srt) * 0.9) - 1)]
        short_pct = sum(1 for l in lens if l <= 80) / len(lens)
        long_pct = sum(1 for l in lens if l >= 200) / len(lens)
    else:
        avg_s = med_s = p90 = 0
        short_pct = long_pct = 0.0

    # Paragraph density
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(full) if p.strip()]
    para_density = (sum(len(p) for p in paragraphs) / len(paragraphs)) if paragraphs else 0.0

    # Structural signals
    structural = []
    if _HEADING_LINE_RE.search(full):
        structural.append("uses_headings")
    if _NUMBERED_LIST_RE.search(full):
        structural.append("numbered_lists")
    if _BULLET_LIST_RE.search(full):
        structural.append("bullet_lists")
    if _QUOTE_LINE_RE.search(full):
        structural.append("quotes_others")
    if _CODE_FENCE_RE.search(full):
        structural.append("code_blocks")

    # Register heuristics — very coarse, calibration is an operator concern
    register = _classify_register(full)

    # Distinctive phrases — recurring 2-4 word phrases by frequency
    phrases = _top_phrases(full, n_gram=(2, 4), max_phrases=15)

    # Formatting notes — operator-facing observations
    formatting_notes: list[str] = []
    if short_pct > 0.5:
        formatting_notes.append("Short sentences dominate (>50% under 80 chars) — keep it punchy.")
    if long_pct > 0.2:
        formatting_notes.append("Substantial use of long sentences (>20% over 200 chars) — comfortable with subordinate clauses.")
    if para_density and para_density < 200:
        formatting_notes.append("Tight paragraphs (avg <200 chars) — frequent visual breaks.")
    elif para_density > 600:
        formatting_notes.append("Dense paragraphs (avg >600 chars) — sustained argument blocks.")
    if "uses_headings" in structural and "bullet_lists" in structural:
        formatting_notes.append("Structured with headings + lists — reader-scannable format.")
    elif "uses_headings" not in structural and "bullet_lists" not in structural:
        formatting_notes.append("Pure prose, no lists — reader expected to follow continuous argument.")

    summary = _render_summary(
        n=len(text_list), avg_s=avg_s, short_pct=short_pct,
        long_pct=long_pct, register=register, structural=structural,
    )

    return StyleSignature(
        n_examples=len(text_list),
        total_chars=total_chars,
        avg_sentence_chars=avg_s,
        median_sentence_chars=med_s,
        p90_sentence_chars=int(p90),
        paragraph_density=para_density,
        short_sentence_pct=short_pct,
        long_sentence_pct=long_pct,
        register=register,
        structural_signals=structural,
        distinctive_phrases=phrases,
        formatting_notes=formatting_notes,
        summary=summary,
    )


# ── Helpers ─────────────────────────────────────────────────────────────


def _classify_register(text: str) -> list[str]:
    """Coarse register classification — heuristic, refined by learning rules."""
    low = text.lower()
    out: list[str] = []
    conversational_signals = ("you know", " i ", "let me", "honestly", "frankly",
                              " we're ", " i'm ", " here's ", " here is the thing")
    if sum(low.count(s) for s in conversational_signals) >= 4:
        out.append("conversational")
    analytical_signals = ("therefore", "however", "consequently", "argues", "evidence",
                          "demonstrates", "consider", "framework")
    if sum(low.count(s) for s in analytical_signals) >= 4:
        out.append("analytical")
    formal_signals = ("furthermore", "notwithstanding", "moreover", "hereby",
                      "wherein", "shall")
    if sum(low.count(s) for s in formal_signals) >= 2:
        out.append("formal")
    instructional_signals = ("first,", "next,", "step ", "to begin", "you should",
                              "you'll want", "tip:")
    if sum(low.count(s) for s in instructional_signals) >= 3:
        out.append("instructional")
    narrative_signals = (" said,", " told ", " remembered", " then ", " walked",
                          " noticed", " realized")
    if sum(low.count(s) for s in narrative_signals) >= 3:
        out.append("narrative")
    return out


_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]*")
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", "shall",
    "to", "of", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above",
    "below", "from", "up", "down", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "just", "i", "you", "he", "she", "it",
    "we", "they", "what", "which", "who", "whom", "this", "that", "these",
    "those", "as", "if",
})


def _top_phrases(text: str, n_gram: tuple[int, int] = (2, 4),
                  max_phrases: int = 15) -> list[str]:
    """Return top recurring 2-4 word phrases (case-insensitive)."""
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return []
    counts: dict[str, int] = {}
    for n in range(n_gram[0], n_gram[1] + 1):
        for i in range(len(words) - n + 1):
            ngram = words[i:i + n]
            # Skip phrases that are all stopwords
            if all(w in _STOPWORDS for w in ngram):
                continue
            phrase = " ".join(ngram)
            counts[phrase] = counts.get(phrase, 0) + 1
    # Keep only phrases that appeared ≥ 2 times
    ranked = sorted(
        ((p, c) for p, c in counts.items() if c >= 2),
        key=lambda x: (-x[1], len(x[0])),
    )
    return [p for p, _ in ranked[:max_phrases]]


def _render_summary(
    n: int, avg_s: float, short_pct: float, long_pct: float,
    register: list[str], structural: list[str],
) -> str:
    bits = [f"Derived from {n} example{'s' if n != 1 else ''}."]
    if avg_s:
        bits.append(f"Average sentence ~{avg_s:.0f} chars.")
    if short_pct > 0.5:
        bits.append("Heavy short-sentence rhythm.")
    elif long_pct > 0.3:
        bits.append("Longer-sentence rhythm with subordinate clauses.")
    if register:
        bits.append(f"Register reads as {'+'.join(register)}.")
    if structural:
        bits.append(f"Uses {', '.join(structural).replace('_', '-')}.")
    return " ".join(bits)


__all__ = ["StyleSignature", "derive_style"]
