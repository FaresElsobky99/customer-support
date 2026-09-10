"""The default tool executor for ``POST /agent/chat``.

Calls the shared service layer directly — the same functions the REST routes use. No MCP
subprocess. This is the enforcement point for the security property in docs/agentic-ai.md
§3: identity (``actor_customer_id`` / ``actor_role``) always comes from ``auth``, which the
route builds from the verified JWT. The model only ever supplies business arguments.
"""

from __future__ import annotations

import json
from functools import partial

import anyio

from backend.app.agent.auth import AuthContext
from backend.app.agent.types import ToolCall, ToolDef, ToolResult
from backend.app.services import customer_service, ticket_service

_NO_ARGS = {"type": "object", "properties": {}}

_GET_CUSTOMER = ToolDef(
    name="get_customer",
    description="Get the authenticated customer's own account record (name, email, status).",
    parameters=_NO_ARGS,
)

_CREATE_TICKET = ToolDef(
    name="create_ticket",
    description=(
        "Open a support ticket for the authenticated customer. Requires a concrete "
        "description of the issue (5-1000 characters)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "issue": {
                "type": "string",
                "description": "What the customer needs help with.",
            }
        },
        "required": ["issue"],
    },
)

_LIST_TICKETS = ToolDef(
    name="list_tickets",
    description=(
        "List support tickets. For a customer this is their own tickets; for an admin it is "
        "every ticket. Pass status='open' or 'closed' to filter."
    ),
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["open", "closed"],
                "description": "Optional status filter.",
            }
        },
    },
)

_GET_TICKET = ToolDef(
    name="get_ticket",
    description="Get one ticket by its numeric id (the caller must be allowed to see it).",
    parameters={
        "type": "object",
        "properties": {"ticket_id": {"type": "integer"}},
        "required": ["ticket_id"],
    },
)

_LIST_ALL_CUSTOMERS = ToolDef(
    name="list_all_customers",
    description="List every customer with their status and role. Admin only.",
    parameters=_NO_ARGS,
)

_UPDATE_TICKET_STATUS = ToolDef(
    name="update_ticket_status",
    description="Set a ticket's status to 'open' or 'closed'. Admin only.",
    parameters={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "integer"},
            "status": {"type": "string", "enum": ["open", "closed"]},
        },
        "required": ["ticket_id", "status"],
    },
)


class ServiceToolExecutor:
    def tool_defs(self, auth: AuthContext) -> list[ToolDef]:
        defs = [_GET_CUSTOMER, _CREATE_TICKET, _LIST_TICKETS, _GET_TICKET]
        if auth.is_admin:
            defs += [_LIST_ALL_CUSTOMERS, _UPDATE_TICKET_STATUS]
        return defs

    async def execute(self, call: ToolCall, auth: AuthContext) -> ToolResult:
        try:
            result = await self._dispatch(call, auth)
        except Exception as error:  # noqa: BLE001 - surface any failure to the model as data
            return _result(call, {"error": f"{type(error).__name__}: {error}"})
        return _result(call, result)

    async def _dispatch(self, call: ToolCall, auth: AuthContext) -> dict:
        args = call.arguments or {}

        if call.name == "get_customer":
            return await _run(
                customer_service.get_customer, auth.customer_id, auth.customer_id, auth.role
            )

        if call.name == "create_ticket":
            issue = args.get("issue")
            if not isinstance(issue, str) or not issue.strip():
                return {"error": "create_ticket requires a non-empty 'issue' string"}
            return await _run(
                ticket_service.create_ticket,
                auth.customer_id,
                issue,
                auth.customer_id,
                auth.role,
            )

        if call.name == "list_tickets":
            status = args.get("status")
            status = status.lower() if isinstance(status, str) and status else None
            return await _run(
                ticket_service.list_tickets,
                auth.customer_id,
                auth.customer_id,
                auth.role,
                status,
            )

        if call.name == "get_ticket":
            ticket_id = _as_int(args.get("ticket_id"))
            if ticket_id is None:
                return {"error": "get_ticket requires an integer 'ticket_id'"}
            return await _run(
                ticket_service.get_ticket, ticket_id, auth.customer_id, auth.role
            )

        if call.name == "list_all_customers":
            if not auth.is_admin:
                return {"error": "Admin access required"}
            return await _run(
                customer_service.list_all_customers, auth.customer_id, auth.role
            )

        if call.name == "update_ticket_status":
            if not auth.is_admin:
                return {"error": "Admin access required"}
            ticket_id = _as_int(args.get("ticket_id"))
            status = args.get("status")
            if ticket_id is None or status not in ("open", "closed"):
                return {
                    "error": "update_ticket_status requires 'ticket_id' (int) and "
                    "'status' ('open' or 'closed')"
                }
            return await _run(
                ticket_service.update_ticket_status,
                ticket_id,
                status,
                auth.customer_id,
                auth.role,
            )

        return {"error": f"Unknown tool: {call.name}"}


def _as_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


async def _run(func, *args) -> dict:
    """Run a blocking (psycopg) service call off the event loop."""
    return await anyio.to_thread.run_sync(partial(func, *args))


def _result(call: ToolCall, payload: dict) -> ToolResult:
    return ToolResult(
        tool_call_id=call.id,
        name=call.name,
        content=json.dumps(payload),
        is_error=isinstance(payload, dict) and "error" in payload,
    )
