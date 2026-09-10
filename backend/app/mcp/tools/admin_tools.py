from backend.app.auth.authorization import authorize_admin
from backend.app.services import customer_service, ticket_service
from backend.app.validation.schemas import (
    ValidationError,
    validate_ticket_id,
    validate_ticket_status,
)


def register_admin_tools(mcp) -> None:
    @mcp.tool()
    def list_all_customers(token: str) -> dict:
        """List all customers for an authenticated admin."""

        user, auth_error = authorize_admin(token)
        if auth_error:
            return auth_error

        return customer_service.list_all_customers(user["customer_id"], user["role"])

    @mcp.tool()
    def update_ticket_status(token: str, ticket_id: int, status: str) -> dict:
        """Set a ticket's status to 'open' or 'closed'. Admin only."""

        try:
            ticket_id = validate_ticket_id(ticket_id)
            status = validate_ticket_status(status)
        except ValidationError as error:
            return {"error": str(error)}

        user, auth_error = authorize_admin(token)
        if auth_error:
            return auth_error

        return ticket_service.update_ticket_status(
            ticket_id, status, user["customer_id"], user["role"]
        )
