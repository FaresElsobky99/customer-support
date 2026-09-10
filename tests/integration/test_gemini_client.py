"""Live smoke test for the Gemini LLM client. Requires GEMINI_API_KEY and network.

Marked `integration` so the fast suite / CI gate skips it. May be skipped at runtime if
Gemini rate-limits (free tier 429s).
"""

import asyncio

import pytest

from backend.app.agent.llm.base import LLMRateLimitError
from backend.app.agent.llm.gemini import GeminiClient
from backend.app.agent.types import Message, ToolDef

pytestmark = pytest.mark.integration


def test_generate_plain_text():
    client = GeminiClient()
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

    assert response.text is not None
    assert response.tool_calls == ()


def test_generate_requests_a_tool():
    client = GeminiClient()
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

    assert any(call.name == "list_tickets" for call in response.tool_calls)
