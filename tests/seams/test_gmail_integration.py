"""Gmail integration tests — MIME builder + addr parser + status helpers."""

from __future__ import annotations

import pytest


@pytest.mark.seam
def test_is_configured_false_by_default(tmp_agency):
    from _framework.integrations.gmail import is_configured
    assert is_configured("any-profile") is False


@pytest.mark.seam
def test_parse_addr_with_name(tmp_agency):
    from _framework.integrations.gmail import _parse_addr
    name, addr = _parse_addr('"Jane Doe" <jane@example.com>')
    assert name == "Jane Doe"
    assert addr == "jane@example.com"


@pytest.mark.seam
def test_parse_addr_without_name(tmp_agency):
    from _framework.integrations.gmail import _parse_addr
    name, addr = _parse_addr("jane@example.com")
    assert name == ""
    assert addr == "jane@example.com"


@pytest.mark.seam
def test_mime_builder_text_only(tmp_agency):
    from _framework.integrations.gmail import _build_mime
    msg = _build_mime(
        to=["a@example.com"], cc=[], bcc=[],
        subject="Hi", body_text="Hello world",
        body_html=None, in_reply_to=None, references=[],
        attachments=[],
    )
    assert msg["To"] == "a@example.com"
    assert msg["Subject"] == "Hi"
    # MIMEText body is base64-encoded by default; get_payload decodes it
    assert "Hello world" in msg.get_payload(decode=True).decode()


@pytest.mark.seam
def test_mime_builder_with_html(tmp_agency):
    from _framework.integrations.gmail import _build_mime
    msg = _build_mime(
        to=["a@example.com"], cc=["c@example.com"], bcc=[],
        subject="Mixed",
        body_text="Plain version",
        body_html="<p>HTML version</p>",
        in_reply_to=None, references=[], attachments=[],
    )
    assert msg.get_content_type() == "multipart/alternative"
    assert msg["Cc"] == "c@example.com"
    parts = msg.get_payload()
    assert len(parts) == 2
    plain_text = parts[0].get_payload(decode=True).decode()
    html_text = parts[1].get_payload(decode=True).decode()
    assert "Plain version" in plain_text
    assert "HTML version" in html_text


@pytest.mark.seam
def test_mime_builder_with_attachment(tmp_path, tmp_agency):
    from _framework.integrations.gmail import _build_mime
    attach = tmp_path / "test.txt"
    attach.write_text("attached content")
    msg = _build_mime(
        to=["a@example.com"], cc=[], bcc=[],
        subject="With attachment", body_text="See attached",
        body_html=None, in_reply_to=None, references=[],
        attachments=[attach],
    )
    s = msg.as_string()
    assert "multipart/mixed" in s
    assert 'filename="test.txt"' in s


@pytest.mark.seam
def test_mime_builder_threading_headers(tmp_agency):
    from _framework.integrations.gmail import _build_mime
    msg = _build_mime(
        to=["a@example.com"], cc=[], bcc=[],
        subject="Re: hi", body_text="reply",
        body_html=None,
        in_reply_to="<msg-id-123@example.com>",
        references=["<msg-id-100@example.com>", "<msg-id-123@example.com>"],
        attachments=[],
    )
    s = msg.as_string()
    assert "In-Reply-To: <msg-id-123@example.com>" in s
    assert "References: <msg-id-100@example.com> <msg-id-123@example.com>" in s


@pytest.mark.seam
def test_scope_presets_defined(tmp_agency):
    from _framework.integrations.gmail import GMAIL_SCOPE_PRESETS
    assert "readonly" in GMAIL_SCOPE_PRESETS
    assert "send" in GMAIL_SCOPE_PRESETS
    assert "modify" in GMAIL_SCOPE_PRESETS
    # modify is a superset (Gmail's modify scope includes send)
    assert any("modify" in s for s in GMAIL_SCOPE_PRESETS["modify"])


@pytest.mark.seam
def test_send_requires_configured(tmp_agency):
    from _framework.integrations.gmail import send_message
    with pytest.raises(RuntimeError, match="not configured"):
        send_message(profile="ghost", to=["a@example.com"],
                     subject="x", body="y")
