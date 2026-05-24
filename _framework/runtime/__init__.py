# FRAMEWORK — owned by HermesAgency. Do not modify in a deployment.
"""
HermesAgency runtime — the inference path inside the framework.

This is what `agency chat` uses to actually talk to a configured
provider. It's the *minimum* end-to-end runtime: provider config
resolver → prompt composer → chat/completions HTTP client.

Hermes (the engine) is still the autonomous runtime for cron-fired
skills. This module is for interactive use — a smoke-test surface,
and the "let me actually USE this thing" entry point.

Public surface:

  from _framework.runtime import (
      resolve_default_provider, ResolvedProvider, ProviderResolveError,
      compose_chat_prompt, ComposedPrompt,
      chat_once, repl, ChatTurn, ChatResult, ChatError,
  )
"""

from __future__ import annotations

from .provider import ResolvedProvider, ProviderResolveError, resolve_default_provider
from .prompt import ComposedPrompt, compose_chat_prompt
from .chat import ChatTurn, ChatResult, ChatError, chat_once, repl

__all__ = [
    "ResolvedProvider", "ProviderResolveError", "resolve_default_provider",
    "ComposedPrompt", "compose_chat_prompt",
    "ChatTurn", "ChatResult", "ChatError", "chat_once", "repl",
]
