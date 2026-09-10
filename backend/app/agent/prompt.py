"""System-prompt assembly for the product agent.

Same content as ``chatbot.py``'s ``system_context``, but sourced in-process (no MCP round
trip): the workflow template from ``backend/app/mcp/prompts.py`` and the policy text from
``support_policy.txt``.
"""

from __future__ import annotations

from backend.app.agent.auth import AuthContext
from backend.app.config import SUPPORT_POLICY_PATH
from backend.app.mcp.prompts import build_support_prompt


def _load_policy() -> str:
    try:
        return SUPPORT_POLICY_PATH.read_text(encoding="utf-8")
    except OSError:
        return "(support policy unavailable)"


# The policy file does not change at runtime — read it once, not once per turn.
_SUPPORT_POLICY = _load_policy()


def assemble_system_prompt(auth: AuthContext) -> str:
    workflow = build_support_prompt("general customer support")
    policy = _SUPPORT_POLICY

    return f"""{workflow}

SUPPORT POLICY:
{policy}

AUTHENTICATION:
The customer is already authenticated as customer_id={auth.customer_id}, role={auth.role}.

RULES:
- Every tool you call acts on this authenticated customer. You cannot act as anyone else.
- Never ask for, or accept, a JWT token, password, or a different customer id.
- Customers can access only their own data. Admins can access all customers.
- If the user asks for data or actions outside their permissions, explain that access is
  denied. Do not attempt the tool call.
- To create a ticket you need a concrete issue description. If it is missing, ask for it.
- Use list_tickets when the user asks about their tickets. Use create_ticket when the
  issue is known and the customer is allowed.
- Explain tool results to the customer in plain language.
"""
