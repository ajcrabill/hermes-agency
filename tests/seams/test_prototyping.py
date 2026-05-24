"""Prototyping subsystem tests — ingest, style derive, iteration tracking."""

from __future__ import annotations

import json
import pytest


# ── Ingest ──────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_ingest_raw_text(tmp_agency):
    from _framework.prototyping import ingest_example
    r = ingest_example("This is just raw text we want to imitate.")
    assert r.format == "raw"
    assert r.chars > 0


@pytest.mark.seam
def test_ingest_local_file(tmp_path, tmp_agency):
    from _framework.prototyping import ingest_example
    p = tmp_path / "ex.md"
    p.write_text("# Title\n\nSome content here.")
    r = ingest_example(str(p))
    assert r.format == "text"
    assert "Title" in r.text


@pytest.mark.seam
def test_ingest_http_with_stub_fetcher(tmp_agency):
    from _framework.prototyping.ingest import IngestResult
    from _framework.prototyping import ingest_example

    def stub(url: str) -> IngestResult:
        return IngestResult(
            source=url, text="Stubbed body. Has two short sentences.",
            format="text", chars=42, metadata={"http_status": 200},
        )
    r = ingest_example("https://example.com/post", fetcher=stub)
    assert r.format == "text"
    assert "Stubbed body" in r.text


@pytest.mark.seam
def test_ingest_handles_html_basic(tmp_agency):
    from _framework.prototyping.ingest import IngestResult, ingest_example
    def stub(url):
        return IngestResult(
            source=url,
            text=ingest_example._html_test_helper() if False else "",
            format="text", chars=0, metadata={},
        )
    # Direct test of the HTML stripper
    from _framework.prototyping.ingest import _strip_html
    html = """<html><head><script>alert('xss')</script></head>
              <body><h1>Title</h1><p>Body text here.</p></body></html>"""
    text = _strip_html(html)
    assert "Title" in text
    assert "Body text here" in text
    assert "alert" not in text
    assert "<" not in text


@pytest.mark.seam
def test_ingest_batch_isolates_errors(tmp_agency):
    from _framework.prototyping import ingest_examples
    results = ingest_examples([
        "Raw 1 — good",
        "/nonexistent/file/that-does-not-exist.txt",
        "Raw 2 — also good",
    ])
    assert len(results) == 3
    assert results[0].format == "raw"
    # The missing file becomes raw text since the file doesn't exist
    # (it's treated as a string, not a file path). That's the documented
    # behavior — explicit Path objects would behave differently.
    assert results[2].format == "raw"


# ── Style ───────────────────────────────────────────────────────────────


@pytest.mark.seam
def test_style_signature_short_sentences(tmp_agency):
    from _framework.prototyping import derive_style
    text = "Short sentence one. Short two. Short three. Short four. Short five. Short six."
    sig = derive_style([text])
    assert sig.n_examples == 1
    assert sig.short_sentence_pct > 0.9
    assert sig.avg_sentence_chars < 40


@pytest.mark.seam
def test_style_signature_detects_structural(tmp_agency):
    from _framework.prototyping import derive_style
    text = """# A heading

Some prose paragraph.

- bullet one
- bullet two
- bullet three

> a quoted line from someone else

1. numbered list item one
2. numbered list item two
"""
    sig = derive_style([text])
    assert "uses_headings" in sig.structural_signals
    assert "bullet_lists" in sig.structural_signals
    assert "numbered_lists" in sig.structural_signals
    assert "quotes_others" in sig.structural_signals


@pytest.mark.seam
def test_style_signature_serializable(tmp_agency):
    from _framework.prototyping import derive_style
    sig = derive_style(["A simple example sentence. Another one here."])
    d = sig.to_dict()
    # round-trip through JSON
    s = json.dumps(d)
    assert "n_examples" in s


@pytest.mark.seam
def test_style_signature_renders_prompt_block(tmp_agency):
    from _framework.prototyping import derive_style
    sig = derive_style(["Short. Brief. Snappy. Tight."])
    block = sig.to_prompt_block()
    assert "Style signature" in block
    assert "Short sentences" in block


# ── Iteration tracking ──────────────────────────────────────────────────


@pytest.mark.seam
def test_prototype_lifecycle(tmp_agency):
    from _framework.prototyping import (
        start_prototype, record_iteration, get_prototype, mark_shipped,
    )

    pid = start_prototype(
        name="Test newsletter — June",
        profile="libra",
        audience="superintendents",
        purpose="announce the workflow",
        example_sources=["raw:example-1"],
        style_signature={"n_examples": 1},
        initial_draft="v0 draft text",
    )
    assert pid > 0

    record_iteration(
        pid, draft_text="v1 draft text",
        feedback="Make the open punchier.",
        change_summary="Tightened opening paragraph.",
        feedback_source="owner",
    )
    record_iteration(
        pid, draft_text="v2 draft text",
        feedback="Now too punchy. Find a middle.",
        change_summary="Brought back one sentence.",
        feedback_source="owner",
    )

    proto = get_prototype(pid)
    assert proto["current_round"] == 2
    assert len(proto["rounds"]) == 3   # round 0 + 2 iterations
    assert proto["rounds"][2].draft_text == "v2 draft text"

    mark_shipped(pid)
    proto = get_prototype(pid)
    assert proto["status"] == "shipped"


@pytest.mark.seam
def test_convergence_diagnostic_stuck(tmp_agency):
    from _framework.prototyping import start_prototype, record_iteration
    from _framework.prototyping.iteration import convergence_diagnostic

    pid = start_prototype(
        name="Stuck loop", profile="libra",
        audience="x", purpose="y", initial_draft="d0",
    )
    # 5 rounds, feedback NOT getting shorter, single reviewer
    feedbacks = [
        "Long feedback A " * 20,
        "Long feedback B " * 20,
        "Long feedback C " * 20,
        "Long feedback D " * 22,
        "Long feedback E " * 23,
    ]
    for fb in feedbacks:
        record_iteration(pid, draft_text="...", feedback=fb,
                          change_summary="ack", feedback_source="owner")

    diag = convergence_diagnostic(pid)
    assert diag["round_count"] == 6   # round 0 + 5 iterations
    assert diag["is_likely_stuck"] is True


@pytest.mark.seam
def test_convergence_diagnostic_converging(tmp_agency):
    from _framework.prototyping import start_prototype, record_iteration
    from _framework.prototyping.iteration import convergence_diagnostic

    pid = start_prototype(
        name="Healthy loop", profile="libra",
        audience="x", purpose="y", initial_draft="d0",
    )
    # 3 rounds, feedback shrinking, multiple reviewers
    record_iteration(pid, draft_text="d1",
                      feedback="Lots to say " * 30,
                      change_summary="ack", feedback_source="owner")
    record_iteration(pid, draft_text="d2",
                      feedback="A few notes",
                      change_summary="ack", feedback_source="kb")
    record_iteration(pid, draft_text="d3",
                      feedback="One nit",
                      change_summary="ack", feedback_source="analyst")

    diag = convergence_diagnostic(pid)
    assert diag["is_likely_stuck"] is False
