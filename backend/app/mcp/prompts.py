def build_support_prompt(issue: str) -> str:
    """The customer-support workflow prompt.

    Shared by the MCP ``support_prompt`` and the product agent
    (``backend/app/agent/prompt.py``) so there is one source of truth.
    """

    return f"""
You are a customer support assistant.

Customer issue:
{issue}

Steps:
1. Authenticate the customer if necessary.
2. Check the customer information.
3. Check the support policy.
4. Ask for missing information.
5. Create a ticket only if the customer is allowed.
6. Explain the result clearly to the customer.
"""


def build_triage_prompt(issue: str) -> str:
    """A workflow prompt for an administrator triaging an incoming ticket."""

    return f"""
You are helping a support administrator triage a ticket.

Ticket:
{issue}

Produce:
1. Category - one of: billing, account, technical, security, other.
2. Priority - high if it is a payment failure, a locked account, or a security concern;
   otherwise normal.
3. Suggested next action - reply and close, reply and keep open, or escalate.
4. A one-paragraph draft reply to the customer.

Base priority and category on the support policy and knowledge base, not guesses.
"""


def register_prompts(mcp) -> None:
    @mcp.prompt()
    def support_prompt(issue: str) -> str:
        """Create a customer support workflow prompt."""

        return build_support_prompt(issue)

    @mcp.prompt()
    def triage_prompt(issue: str) -> str:
        """Create a ticket-triage workflow prompt for an administrator."""

        return build_triage_prompt(issue)
