"""Live smoke test for the Gemini LLM client.

Requires GEMINI_API_KEY (or GOOGLE_API_KEY) and network. Marked `integration` so the fast
suite / CI gate skips it; skipped at runtime if the key is missing or Gemini rate-limits.
"""

import asyncio
import os

import pytest

from backend.app.agent.llm.base import LLMError, LLMRateLimitError
from backend.app.agent.types import Message, ToolDef

pytestmark = pytest.mark.integration


def _client():
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        pytest.skip("GEMINI_API_KEY not set")
    from backend.app.agent.llm.gemini import GeminiClient

    return GeminiClient()


def test_generate_plain_text():
    client = _client()
    try:
        response = asyncio.run(
            client.generate(
                system="You are terse.",
                messages=[Message(role="user", text="Reply with exactly: pong")],
                tools=[],
            )
        )
    except LLMRateLimitError:
        pytest.skip("Gemini rate-limited")
    except LLMError as error:
        pytest.skip(f"Gemini unavailable: {error}")

    assert response.text is not None
    assert response.tool_calls == ()


def test_generate_requests_a_tool():
    client = _client()
    tool = ToolDef(
        name="list_tickets",
        description="List the customer's support tickets.",
        parameters={"type": "object", "properties": {}},
    )
    try:
        response = asyncio.run(
            client.generate(
                system="Use tools when the user asks about their tickets.",
                messages=[Message(role="user", text="What tickets do I have open?")],
                tools=[tool],
            )
        )
    except LLMRateLimitError:
        pytest.skip("Gemini rate-limited")
    except LLMError as error:
        pytest.skip(f"Gemini unavailable: {error}")

    assert any(call.name == "list_tickets" for call in response.tool_calls)
