"""The LLM interface the agent depends on. One method: ``generate``.

Deliberately minimal — this application needs "chat with tools" and nothing else. No
embeddings, no vision, no streaming (a ``generate_stream`` can be added later without
breaking callers).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from backend.app.agent.types import LLMResponse, Message, ToolDef


class LLMError(RuntimeError):
    """The provider failed in a way the caller cannot retry around."""


class LLMRateLimitError(LLMError):
    """The provider is rate-limiting (e.g. Gemini free-tier HTTP 429)."""


@runtime_checkable
class LLMClient(Protocol):
    async def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDef],
    ) -> LLMResponse:
        """Run one model turn over the full message list and return its response."""
        ...
