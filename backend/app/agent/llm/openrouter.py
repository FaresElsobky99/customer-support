"""OpenRouter implementation of ``LLMClient``.

OpenRouter (https://openrouter.ai) is a single API in front of many models, including
several **free** ones. It speaks the OpenAI Chat Completions format.

Setup:
1. Create a free account at https://openrouter.ai (sign in with Google/GitHub).
2. Settings -> Keys -> Create API Key. Copy the ``sk-or-v1-...`` value.
3. Put it in ``.env``:  ``OPENROUTER_API_KEY=sk-or-v1-...``
4. ``LLM_PROVIDER=openrouter`` (and optionally ``OPENROUTER_MODEL=...``).

There is no shared/public key — each account gets its own, and free models are still
rate-limited per account (roughly 20 requests/min, 50-1000/day).

The agent needs **tool calling**, so the model must support it. Default is
``openrouter/free`` — a meta-model that auto-routes to whatever free tool-capable model is
available, so it survives individual models being retired. To pin a specific one, set
``OPENROUTER_MODEL`` and check https://openrouter.ai/models?max_price=0 (filter for "Tools").
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

import httpx

# Loads .env so OPENROUTER_API_KEY is available outside the FastAPI app too.
import backend.app.config  # noqa: F401
from backend.app.agent.llm.base import LLMError, LLMRateLimitError
from backend.app.agent.types import LLMResponse, Message, ToolCall, ToolDef

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
REQUEST_TIMEOUT = 120.0


class OpenRouterClient:
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self._model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")

    async def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDef],
    ) -> LLMResponse:
        if not self._api_key:
            raise LLMError(
                "OPENROUTER_API_KEY is not set. Create a free key at "
                "https://openrouter.ai/settings/keys and add it to .env."
            )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": _to_openai_messages(system, messages),
        }
        if tools:
            payload["tools"] = [_to_openai_tool(tool) for tool in tools]
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Title": "mcp-customer-support",
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(API_URL, json=payload, headers=headers)
        except httpx.HTTPError as error:
            raise LLMError(f"OpenRouter request failed: {error}") from error

        if response.status_code == 429:
            raise LLMRateLimitError("OpenRouter rate limit (HTTP 429)")
        if response.status_code >= 400:
            raise LLMError(f"OpenRouter HTTP {response.status_code}: {response.text[:500]}")

        return _parse_response(response.json())


def _to_openai_tool(tool: ToolDef) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def _to_openai_messages(system: str, messages: Sequence[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]

    for message in messages:
        if message.role == "user":
            out.append({"role": "user", "content": message.text or ""})

        elif message.role == "assistant":
            if message.tool_calls:
                # OpenAI format: content is null (not "") on a tool-call turn.
                out.append(
                    {
                        "role": "assistant",
                        "content": message.text or None,
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.name,
                                    "arguments": json.dumps(call.arguments),
                                },
                            }
                            for call in message.tool_calls
                        ],
                    }
                )
            else:
                out.append({"role": "assistant", "content": message.text or ""})

        elif message.role == "tool":
            for result in message.tool_results:
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": result.tool_call_id,
                        "content": result.content,
                    }
                )

    return out


def _parse_response(body: dict[str, Any]) -> LLMResponse:
    choices = body.get("choices") or []
    if not choices:
        # OpenRouter surfaces upstream errors in an "error" object even on HTTP 200.
        error = body.get("error")
        if error:
            message = str(error.get("message", error))
            if error.get("code") == 429 or "rate" in message.lower():
                raise LLMRateLimitError(f"OpenRouter: {message}")
            raise LLMError(f"OpenRouter: {message}")
        return LLMResponse(text="", tool_calls=(), raw=body)

    message = choices[0].get("message") or {}
    raw_tool_calls = message.get("tool_calls") or []

    tool_calls: list[ToolCall] = []
    for index, call in enumerate(raw_tool_calls):
        function = call.get("function") or {}
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        tool_calls.append(
            ToolCall(
                id=call.get("id") or f"{function.get('name', 'tool')}-{index}",
                name=function.get("name", ""),
                arguments=arguments,
            )
        )

    return LLMResponse(
        text=message.get("content") or None,
        tool_calls=tuple(tool_calls),
        raw=body,
    )
