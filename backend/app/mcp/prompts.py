def register_prompts(mcp) -> None:
    @mcp.prompt()
    def support_prompt(issue: str) -> str:
        """Create a customer support workflow prompt."""

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
