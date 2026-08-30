from backend.app.auth.authorization import authorize_customer
from backend.app.services import customer_service, ticket_service
from backend.app.validation.schemas import (
    ValidationError,
    validate_customer_id,
    validate_customer_name,
    validate_ticket_issue,
)


def register_customer_tools(mcp) -> None:
    @mcp.tool()
    def hello_customer(name: str) -> str | dict:
        """Return a greeting for a customer."""

        try:
            name = validate_customer_name(name)
        except ValidationError as error:
            return {"error": str(error)}

        return f"Hello {name}, how can I assist you today?"

    @mcp.tool()
    def get_customer(token: str, customer_id: int) -> dict:
        """Get customer information if authorized."""

        try:
            customer_id = validate_customer_id(customer_id)
        except ValidationError as error:
            return {"error": str(error)}

        user, auth_error = authorize_customer(token, customer_id)
        if auth_error:
            return auth_error

        return customer_service.get_customer(customer_id, user["customer_id"], user["role"])

    @mcp.tool()
    def create_ticket(token: str, customer_id: int, issue: str) -> dict:
        """Create a support ticket for an active customer."""

        try:
            customer_id = validate_customer_id(customer_id)
            issue = validate_ticket_issue(issue)
        except ValidationError as error:
            return {"error": str(error)}

        user, auth_error = authorize_customer(token, customer_id)
        if auth_error:
            return auth_error

        return ticket_service.create_ticket(
            customer_id,
            issue,
            user["customer_id"],
            user["role"],
        )

    @mcp.tool()
    def list_tickets(token: str, customer_id: int) -> dict:
        """List support tickets for a customer if authorized."""

        try:
            customer_id = validate_customer_id(customer_id)
        except ValidationError as error:
            return {"error": str(error)}

        user, auth_error = authorize_customer(token, customer_id)
        if auth_error:
            return auth_error

        return ticket_service.list_tickets(customer_id, user["customer_id"], user["role"])
