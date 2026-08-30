from backend.app.config import SUPPORT_POLICY_PATH


def register_resources(mcp) -> None:
    @mcp.resource("file://support-policy")
    def support_policy() -> str:
        """Return the customer support policy."""

        return SUPPORT_POLICY_PATH.read_text(encoding="utf-8")
