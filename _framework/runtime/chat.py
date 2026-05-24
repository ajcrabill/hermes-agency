# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
Interactive chat client.

The minimum end-to-end inference path inside HermesAgency. Loads the
profile's persona + standards + applicable learning rules, sends a
message to the configured provider, prints the response.

This is what `agency chat` calls. It uses stdlib only (urllib + json)
so the framework picks up no new dependencies for a built-in chat
surface.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

from _framework.runtime.provider import ResolvedProvider, ProviderResolveError, resolve_default_provider
from _framework.runtime.prompt import compose_chat_prompt


@dataclass
class ChatTurn:
    role: str          # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatResult:
    response: str
    model: str
    provider: str
    rules_in_context: int
    tokens_in: int | None = None
    tokens_out: int | None = None


def chat_once(
    user_message: str,
    *,
    profile: str = "loriah",
    role: str = "chief-of-staff",
    voice_tags: list[str] | None = None,
    history: list[ChatTurn] | None = None,
    skill_tag: str = "interactive-chat",
) -> ChatResult:
    """One round-trip: send `user_message` (plus optional history),
    return the model's response.

    Raises ProviderResolveError if deployment.yaml is misconfigured.
    Raises ChatError if the inference call fails.
    """
    provider = resolve_default_provider()
    composed = compose_chat_prompt(
        profile=profile, role=role,
        voice_tags=voice_tags or [],
        skill_tag=skill_tag,
    )

    messages: list[dict] = [{"role": "system", "content": composed.system}]
    for h in (history or []):
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": user_message})

    body = {
        "model": provider.model,
        "messages": messages,
        "stream": False,
    }
    body_bytes = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url=f"{provider.base_url}/chat/completions",
        data=body_bytes,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **({"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=provider.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:600]
        raise ChatError(
            f"Provider HTTP {e.code} {e.reason}\n"
            f"  endpoint: {provider.base_url}/chat/completions\n"
            f"  model:    {provider.model}\n"
            f"  body:     {err_body}"
        ) from e
    except urllib.error.URLError as e:
        raise ChatError(
            f"Provider connection failed: {e.reason}\n"
            f"  endpoint: {provider.base_url}/chat/completions\n"
            f"  Check the base_url in deployment.yaml is reachable from here."
        ) from e

    try:
        choice = payload["choices"][0]
        text = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ChatError(
            f"Provider returned a payload we didn't understand:\n"
            f"  {json.dumps(payload)[:600]}"
        ) from e

    usage = payload.get("usage") or {}
    return ChatResult(
        response=text,
        model=provider.model,
        provider=provider.name,
        rules_in_context=composed.rules_count,
        tokens_in=usage.get("prompt_tokens"),
        tokens_out=usage.get("completion_tokens"),
    )


class ChatError(RuntimeError):
    """Raised when the inference call fails."""


def repl(
    *, profile: str = "loriah",
    role: str = "chief-of-staff",
    voice_tags: list[str] | None = None,
    skill_tag: str = "interactive-chat",
) -> int:
    """Interactive REPL — type messages, see responses, ^C / 'exit' to quit.

    Returns CLI exit code.
    """
    try:
        provider = resolve_default_provider()
    except ProviderResolveError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    composed = compose_chat_prompt(
        profile=profile, role=role,
        voice_tags=voice_tags or [],
        skill_tag=skill_tag,
    )

    print(f"agency chat — {profile} (role: {role})")
    print(f"  provider: {provider.name}  model: {provider.model}")
    print(f"  context:  {composed.rules_count} learning rule(s) injected")
    print(f"  type 'exit' or ^D to quit; ^C to interrupt a response\n")

    history: list[ChatTurn] = []
    while True:
        try:
            user_input = input(f"{profile} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", ":q"):
            break

        try:
            result = chat_once(
                user_input,
                profile=profile, role=role,
                voice_tags=voice_tags or [],
                history=history,
                skill_tag=skill_tag,
            )
        except (ChatError, ProviderResolveError) as e:
            print(f"\n✗ {e}\n", file=sys.stderr)
            continue
        except KeyboardInterrupt:
            print("\n  (interrupted)\n")
            continue

        print(f"\n{result.response}\n")
        if result.tokens_in is not None:
            print(f"  · {result.tokens_in} in / {result.tokens_out} out tokens\n")

        history.append(ChatTurn(role="user", content=user_input))
        history.append(ChatTurn(role="assistant", content=result.response))

    print("bye.")
    return 0


__all__ = [
    "ChatTurn", "ChatResult", "ChatError",
    "chat_once", "repl",
]
