"""Tool executor that goes through the MCP server over stdio.

Used only by ``chatbot.py`` — it keeps the MCP path exercised and serves as the reference
for how an external MCP client (Claude Desktop, an IDE) would consume this server. The HTTP
endpoint uses ``ServiceToolExecutor`` instead (see docs/agentic-ai.md §8).

This is the identity-injection logic that used to be inline in ``chatbot.py``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from backend.app.agent.auth import AuthContext
from backend.app.agent.types import ToolCall, ToolDef, ToolResult

# Tools that take a JWT the model must never see.
PROTECTED_TOOLS = {
    "get_customer",
    "create_ticket",
    "list_tickets",
    "get_ticket",
    "list_all_customers",
    "update_ticket_status",
}
# Tools scoped to a single customer whose id the app injects.
CUSTOMER_SCOPED_TOOLS = {"get_customer", "create_ticket", "list_tickets"}
# Tools only an admin may call.
ADMIN_TOOLS = {"list_all_customers", "update_ticket_status"}


def _is_error_payload(text: str) -> bool:
    """True only if the tool returned a JSON object with an ``error`` key."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(payload, dict) and "error" in payload


class McpToolExecutor:
    def __init__(self, client, raw_tools: Iterable) -> None:
        self._client = client
        self._raw_tools = list(raw_tools)

    def tool_defs(self, auth: AuthContext) -> list[ToolDef]:
        defs: list[ToolDef] = []

        for tool in self._raw_tools:
            if tool.name == "login":
                continue
            if tool.name in ADMIN_TOOLS and not auth.is_admin:
                continue

            schema = dict(tool.input_schema or {})
            properties = dict(schema.get("properties", {}))
            required = [r for r in schema.get("required", []) if r in properties]

            for hidden in ("token", "customer_id"):
                if (
                    tool.name in PROTECTED_TOOLS
                    or tool.name in CUSTOMER_SCOPED_TOOLS
                ) and hidden in properties:
                    properties.pop(hidden, None)
                    if hidden in required:
                        required.remove(hidden)

            schema["properties"] = properties
            schema["required"] = required
            defs.append(
                ToolDef(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=schema,
                )
            )

        return defs

    async def execute(self, call: ToolCall, auth: AuthContext) -> ToolResult:
        args = dict(call.arguments or {})
        if call.name in PROTECTED_TOOLS and auth.token:
            args["token"] = auth.token
        if call.name in CUSTOMER_SCOPED_TOOLS:
            args["customer_id"] = auth.customer_id

        try:
            result = await self._client.call_tool(call.name, args)
        except Exception as error:  # noqa: BLE001
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"error": f"{type(error).__name__}: {error}"}),
                is_error=True,
            )

        text = result.content[0].text if result.content else "{}"
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=text,
            is_error=_is_error_payload(text),
        )
