"""Provider-neutral representation of a tool-using conversation.

Every LLM client (llm/gemini.py, a future llm/claude.py) translates to and from these
types, so the rest of the agent — the runner, the executors, the endpoint — never touches
a vendor SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant", "tool"]


@dataclass(frozen=True)
class ToolDef:
    """A tool offered to the model. ``parameters`` is a JSON Schema object describing only
    the real business arguments — identity args (token, customer_id) are never present."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """The model's request to run a tool. ``id`` is synthesized for providers (Gemini)
    that correlate calls and results by name/order rather than an explicit id.

    ``provider_meta`` is opaque per-provider data that must survive a round trip when the
    assistant turn is replayed (e.g. Gemini 3's ``thought_signature``). The runner and the
    executors never read it; only the LLM client that produced it does.
    """

    id: str
    name: str
    arguments: dict[str, Any]
    provider_meta: Any = None


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    name: str
    content: str  # JSON string
    is_error: bool = False


@dataclass(frozen=True)
class Message:
    role: Role
    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(frozen=True)
class LLMResponse:
    """One turn from the model. Empty ``tool_calls`` means the turn is final."""

    text: str | None
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    raw: Any = None
