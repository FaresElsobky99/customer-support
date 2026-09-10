"""Gemini implementation of ``LLMClient``.

This is the translation layer that used to live inline in ``chatbot.py`` (the tool-schema
conversion around lines 146-193 and the response parsing in the tool loop). It now has one
home.

Quirk: Gemini correlates a function response to its call by **name and order**, not by an
id. ``ToolCall.id`` is synthesized elsewhere and only matters to providers that need it.
"""

from __future__ import annotations

import json
import os
from typing import Sequence

from google import genai
from google.genai import errors, types

# Importing config loads .env, so GEMINI_API_KEY is present before genai.Client() is built
# even when the agent is used outside the FastAPI app (scripts, the chatbot).
import backend.app.config  # noqa: F401
from backend.app.agent.llm.base import LLMError, LLMRateLimitError
from backend.app.agent.types import LLMResponse, Message, ToolCall, ToolDef

DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiClient:
    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        # Built lazily: genai.Client() validates GEMINI_API_KEY / GOOGLE_API_KEY at
        # construction, and this client is created via a FastAPI dependency that must not
        # fail just because a different provider is configured.
        if self._client is None:
            self._client = genai.Client()
        return self._client

    async def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolDef],
    ) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[_to_gemini_tool(tools)] if tools else None,
            # We run our own tool loop (AgentRunner). Stop the SDK from trying to execute
            # tool calls itself, and silence its AFC warning.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        try:
            response = await self._get_client().aio.models.generate_content(
                model=self._model,
                contents=_to_gemini_contents(messages),
                config=config,
            )
        except errors.APIError as error:
            # APIError covers both ClientError (4xx) and ServerError (5xx) — free-tier
            # Gemini 503s a lot, and a retired model is a 404.
            if getattr(error, "code", None) == 429:
                raise LLMRateLimitError("Gemini rate limit (HTTP 429)") from error
            raise LLMError(f"Gemini error: {error}") from error
        except Exception as error:  # noqa: BLE001 - transport/parse failures must not 500
            raise LLMError(f"Gemini request failed: {error}") from error

        return _parse_response(response)


def _to_gemini_tool(tools: Sequence[ToolDef]) -> types.Tool:
    return types.Tool(
        function_declarations=[
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]
    )


def _to_gemini_contents(messages: Sequence[Message]) -> list[types.Content]:
    contents: list[types.Content] = []

    for message in messages:
        if message.role == "user":
            contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=message.text or "")])
            )

        elif message.role == "assistant":
            parts: list[types.Part] = []
            if message.text:
                parts.append(types.Part.from_text(text=message.text))
            for call in message.tool_calls:
                part = types.Part(
                    function_call=types.FunctionCall(
                        name=call.name, args=dict(call.arguments)
                    )
                )
                # Gemini 3 requires the thought_signature from the original response to be
                # echoed back on the function_call part.
                meta = call.provider_meta or {}
                if meta.get("thought_signature"):
                    part.thought_signature = meta["thought_signature"]
                parts.append(part)
            contents.append(types.Content(role="model", parts=parts))

        elif message.role == "tool":
            parts = []
            for result in message.tool_results:
                try:
                    payload = json.loads(result.content)
                except json.JSONDecodeError:
                    payload = {"message": result.content}
                parts.append(
                    types.Part.from_function_response(
                        name=result.name,
                        response={
                            "success": not result.is_error,
                            "data": payload,
                        },
                    )
                )
            contents.append(types.Content(role="user", parts=parts))

    return contents


def _parse_response(response: object) -> LLMResponse:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return LLMResponse(text="", tool_calls=(), raw=response)

    parts = getattr(candidates[0].content, "parts", None) or []
    text_chunks: list[str] = []
    tool_calls: list[ToolCall] = []

    for index, part in enumerate(parts):
        function_call = getattr(part, "function_call", None)
        if function_call is not None:
            signature = getattr(part, "thought_signature", None)
            tool_calls.append(
                ToolCall(
                    id=function_call.id or f"{function_call.name}-{index}",
                    name=function_call.name,
                    arguments=dict(function_call.args or {}),
                    provider_meta={"thought_signature": signature} if signature else None,
                )
            )
        elif getattr(part, "text", None):
            text_chunks.append(part.text)

    return LLMResponse(
        text="".join(text_chunks) or None,
        tool_calls=tuple(tool_calls),
        raw=response,
    )
