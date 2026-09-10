"""Provider selection. ``LLM_PROVIDER`` env var, default ``gemini``.

- ``gemini``     — Google Gemini (needs ``GEMINI_API_KEY``).
- ``openrouter`` — OpenRouter, incl. free models (needs ``OPENROUTER_API_KEY``,
  optional ``OPENROUTER_MODEL``). See ``llm/openrouter.py`` for setup.

Adding another: write ``llm/<name>.py`` with a client implementing ``LLMClient``, then add
one branch here (e.g. ``llm/claude.py`` — the ``anthropic`` package is already installed).
"""

from __future__ import annotations

import os

from backend.app.agent.llm.base import LLMClient, LLMError


def get_llm(provider: str | None = None) -> LLMClient:
    provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()

    if provider == "gemini":
        from backend.app.agent.llm.gemini import GeminiClient

        return GeminiClient()

    if provider == "openrouter":
        from backend.app.agent.llm.openrouter import OpenRouterClient

        return OpenRouterClient()

    # if provider == "claude":
    #     from backend.app.agent.llm.claude import ClaudeClient
    #     return ClaudeClient()

    raise LLMError(f"Unknown LLM_PROVIDER: {provider!r}")
