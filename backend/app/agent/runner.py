"""The agentic loop, shared by ``POST /agent/chat`` and ``chatbot.py``.

Same shape as the ``while True`` block in ``chatbot.py`` (lines ~239-324), with the fixes
it was missing: a ``max_steps`` cap so a confused model cannot loop forever, and graceful
handling of every provider failure (not just rate limits).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from backend.app.agent.auth import AuthContext
from backend.app.agent.llm.base import LLMClient, LLMError, LLMRateLimitError
from backend.app.agent.prompt import assemble_system_prompt
from backend.app.agent.tools.executor import ToolExecutor
from backend.app.agent.types import Message

StoppedReason = Literal["final", "max_steps", "rate_limited", "error"]

_MAX_STEPS_REPLY = (
    "I wasn't able to finish that in the steps I have available. Could you rephrase or "
    "break it into smaller parts?"
)
_RATE_LIMITED_REPLY = (
    "The assistant is briefly rate-limited. Please try again in a few moments."
)
_ERROR_REPLY = (
    "The assistant is having trouble right now. Please try again in a few moments."
)


def _default_max_steps() -> int:
    try:
        return max(1, int(os.getenv("AGENT_MAX_STEPS", "6")))
    except (TypeError, ValueError):
        return 6


@dataclass
class AgentResult:
    reply: str
    history: list[Message]
    tool_calls: list[str] = field(default_factory=list)
    steps: int = 0
    stopped_reason: StoppedReason = "final"


class AgentRunner:
    def __init__(
        self,
        llm: LLMClient,
        executor: ToolExecutor,
        *,
        max_steps: int | None = None,
    ) -> None:
        self._llm = llm
        self._executor = executor
        self._max_steps = max(1, max_steps if max_steps is not None else _default_max_steps())

    async def run(
        self,
        *,
        auth: AuthContext,
        history: list[Message],
        user_message: str,
    ) -> AgentResult:
        system = assemble_system_prompt(auth)
        tools = self._executor.tool_defs(auth)

        messages: list[Message] = list(history) + [Message(role="user", text=user_message)]
        invoked: list[str] = []

        for step in range(1, self._max_steps + 1):
            try:
                response = await self._llm.generate(
                    system=system, messages=messages, tools=tools
                )
            except LLMRateLimitError:
                return self._bail(messages, invoked, step - 1, "rate_limited", _RATE_LIMITED_REPLY)
            except LLMError:
                return self._bail(messages, invoked, step - 1, "error", _ERROR_REPLY)

            if not response.tool_calls:
                reply = response.text or ""
                return self._bail(messages, invoked, step, "final", reply)

            # Out of budget: don't execute more tool calls (they have side effects the
            # model would never see the result of), just stop.
            if step == self._max_steps:
                break

            messages.append(
                Message(
                    role="assistant",
                    text=response.text,
                    tool_calls=response.tool_calls,
                )
            )

            results = []
            for call in response.tool_calls:
                invoked.append(call.name)
                results.append(await self._executor.execute(call, auth))
            messages.append(Message(role="tool", tool_results=tuple(results)))

        return self._bail(messages, invoked, self._max_steps, "max_steps", _MAX_STEPS_REPLY)

    @staticmethod
    def _bail(
        messages: list[Message],
        invoked: list[str],
        steps: int,
        reason: StoppedReason,
        reply: str,
    ) -> AgentResult:
        messages.append(Message(role="assistant", text=reply))
        return AgentResult(
            reply=reply,
            history=messages,
            tool_calls=invoked,
            steps=steps,
            stopped_reason=reason,
        )
