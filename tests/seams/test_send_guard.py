"""Send-guard seam tests — access list + hard ceilings + hard-rule validators."""

from __future__ import annotations

import textwrap

import pytest


@pytest.mark.seam
def test_allow_clean_send(tmp_agency):
    from _framework.send_guard import evaluate, SendCandidate
    from _framework.send_guard.send_guard import Verdict
    cand = SendCandidate(
        to=["friend@example.com"],
        from_addr="agency@example.com",
        subject="Hello",
        body="World",
        skill="send-orchestrator",
        profile="loriah",
        intended_action_class="send-single",
    )
    decision = evaluate(cand)
    assert decision.verdict == Verdict.ALLOW


@pytest.mark.seam
def test_no_recipients_denies(tmp_agency):
    from _framework.send_guard import evaluate, SendCandidate
    from _framework.send_guard.send_guard import Verdict
    cand = SendCandidate(to=[])
    decision = evaluate(cand)
    assert decision.verdict == Verdict.DENY
    assert any("no recipients" in r for r in decision.reasons)


@pytest.mark.seam
def test_malformed_address_denies(tmp_agency):
    from _framework.send_guard import evaluate, SendCandidate
    from _framework.send_guard.send_guard import Verdict
    cand = SendCandidate(to=["not-an-email"])
    decision = evaluate(cand)
    assert decision.verdict == Verdict.DENY


@pytest.mark.seam
def test_blacklist_denies_and_records_firing(tmp_agency):
    from _framework.send_guard import evaluate, SendCandidate
    from _framework.send_guard.send_guard import Verdict, AccessList
    access = AccessList(blacklist={"villain@evil.example"})
    cand = SendCandidate(
        to=["villain@evil.example"],
        from_addr="agency@example.com",
    )
    decision = evaluate(cand, access_list=access)
    assert decision.verdict == Verdict.DENY
    assert decision.firings
    assert decision.firings[0]["was_overridden"] is True


@pytest.mark.seam
def test_greylist_holds_for_review(tmp_agency):
    from _framework.send_guard import evaluate, SendCandidate
    from _framework.send_guard.send_guard import Verdict, AccessList
    access = AccessList(greylist={"maybe@unsure.example"})
    cand = SendCandidate(
        to=["maybe@unsure.example"],
        from_addr="agency@example.com",
    )
    decision = evaluate(cand, access_list=access)
    assert decision.verdict == Verdict.HOLD


@pytest.mark.seam
def test_first_message_holds(tmp_agency):
    from _framework.send_guard import evaluate, SendCandidate
    from _framework.send_guard.send_guard import Verdict
    cand = SendCandidate(
        to=["new-prospect@example.com"],
        from_addr="agency@example.com",
        is_first_message=True,
    )
    decision = evaluate(cand)
    # Hard ceiling 'new-contact-first-message' → HOLD
    assert decision.verdict == Verdict.HOLD


@pytest.mark.seam
def test_access_list_parses_markdown(tmp_path, tmp_agency):
    from _framework.send_guard import load_access_list
    md = textwrap.dedent(
        """
        # Email Access List

        ## Whitelist
        - friend@example.com
        - colleague@example.com  # trusted

        ## Greylist
        - unsure@example.com

        ## Blacklist
        - villain@evil.example
        """
    )
    p = tmp_path / "email-access.md"
    p.write_text(md)
    al = load_access_list(p)
    assert "friend@example.com" in al.whitelist
    assert "unsure@example.com" in al.greylist
    assert "villain@evil.example" in al.blacklist
