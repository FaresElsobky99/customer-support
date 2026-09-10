from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.app.agent.auth import AuthContext
from backend.app.agent.types import ToolCall, ToolDef, ToolResult


@runtime_checkable
class ToolExecutor(Protocol):
    """Supplies the tool list and runs tool calls, always scoped to ``auth``.

    Implementations must:
    - return only tools the caller's role is allowed to use from ``tool_defs``;
    - never let a tool argument override identity — ``auth`` is the sole source of
      customer_id / role.
    """

    def tool_defs(self, auth: AuthContext) -> list[ToolDef]: ...

    async def execute(self, call: ToolCall, auth: AuthContext) -> ToolResult: ...
