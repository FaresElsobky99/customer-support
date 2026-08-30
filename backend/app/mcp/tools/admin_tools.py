from backend.app.auth.authorization import authorize_admin
from backend.app.services import customer_service


def register_admin_tools(mcp) -> None:
    @mcp.tool()
    def list_all_customers(token: str) -> dict:
        """List all customers for an authenticated admin."""

        user, auth_error = authorize_admin(token)
        if auth_error:
            return auth_error

        return customer_service.list_all_customers(user["customer_id"], user["role"])
