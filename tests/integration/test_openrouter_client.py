"""Live smoke test for the OpenRouter LLM client.

Requires OPENROUTER_API_KEY and network. Marked `integration` so the fast suite skips it;
skipped at runtime if the key is missing or the free model is rate-limited.
"""

import asyncio
import os

import pytest

from backend.app.agent.llm.base import LLMError, LLMRateLimitError
from backend.app.agent.llm.openrouter import OpenRouterClient
from backend.app.agent.types import Message, ToolDef

pytestmark = pytest.mark.integration


def _client() -> OpenRouterClient:
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")
    return OpenRouterClient()


def test_generate_plain_text():
    try:
        response = asyncio.run(
            _client().generate(
                system="You are terse.",
                messages=[Message(role="user", text="Reply with exactly: pong")],
                tools=[],
            )
        )
    except LLMRateLimitError:
        pytest.skip("OpenRouter rate-limited")
    except LLMError as error:
        pytest.skip(f"OpenRouter unavailable: {error}")

    assert response.text is not None


def test_generate_requests_a_tool():
    tool = ToolDef(
        name="list_tickets",
        description="List the customer's support tickets.",
        parameters={"type": "object", "properties": {}},
    )
    try:
        response = asyncio.run(
            _client().generate(
                system="Use the list_tickets tool when the user asks about their tickets.",
                messages=[Message(role="user", text="What tickets do I have open?")],
                tools=[tool],
            )
        )
    except LLMRateLimitError:
        pytest.skip("OpenRouter rate-limited")
    except LLMError as error:
        pytest.skip(f"OpenRouter unavailable: {error}")

    assert any(call.name == "list_tickets" for call in response.tool_calls)
