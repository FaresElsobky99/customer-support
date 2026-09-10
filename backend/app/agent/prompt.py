"""System-prompt assembly for the product agent.

Same content as ``chatbot.py``'s ``system_context`` but sourced in-process, plus a
knowledge base and role-specific guidance. The policy and FAQ files do not change at
runtime, so they are read once at import.
"""

from __future__ import annotations

from backend.app.agent.auth import AuthContext
from backend.app.config import FAQ_PATH, SUPPORT_POLICY_PATH
from backend.app.mcp.prompts import build_support_prompt


def _read(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "(unavailable)"


_SUPPORT_POLICY = _read(SUPPORT_POLICY_PATH)
_FAQ = _read(FAQ_PATH)

_CUSTOMER_RULES = """\
- You are speaking directly to the customer. Be concise and friendly.
- Every tool you call acts on this authenticated customer. You cannot act as anyone else.
- Never ask for, or accept, a JWT token, password, or a different customer id.
- If the customer asks for data or actions outside their permissions, explain that access
  is denied. Do not attempt the tool call.
- To create a ticket you need a concrete issue description. If it is missing, ask for it.
- Use get_ticket / list_tickets to answer questions about the customer's tickets.
- Explain tool results in plain language."""

_ADMIN_RULES = """\
- You are assisting a support administrator. Be direct and information-dense.
- You can read every customer and every ticket, and set a ticket's status with
  update_ticket_status.
- Before closing a ticket, make sure the customer's issue is actually resolved or the
  ticket is a duplicate; say why you are closing it.
- When asked to triage, classify category and priority from the support policy and
  knowledge base (payment failure, locked account, and security concerns are high
  priority) and propose a next action.
- Explain what each tool call returned."""


def assemble_system_prompt(auth: AuthContext) -> str:
    workflow = build_support_prompt("general customer support")
    rules = _ADMIN_RULES if auth.is_admin else _CUSTOMER_RULES

    return f"""{workflow}

SUPPORT POLICY:
{_SUPPORT_POLICY}

KNOWLEDGE BASE:
{_FAQ}

AUTHENTICATION:
The caller is authenticated as customer_id={auth.customer_id}, role={auth.role}.

RULES:
{rules}
"""
