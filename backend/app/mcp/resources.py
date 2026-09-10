from backend.app.config import FAQ_PATH, SUPPORT_POLICY_PATH


def register_resources(mcp) -> None:
    @mcp.resource("file://support-policy")
    def support_policy() -> str:
        """Return the customer support policy."""

        return SUPPORT_POLICY_PATH.read_text(encoding="utf-8")

    @mcp.resource("file://faq")
    def faq() -> str:
        """Return the support knowledge base (account status, tickets, common questions)."""

        try:
            return FAQ_PATH.read_text(encoding="utf-8")
        except OSError:
            return "(knowledge base unavailable)"
