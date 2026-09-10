from backend.app.auth.authorization import authorize_customer
from backend.app.auth.jwt import verify_token
from backend.app.services import customer_service, ticket_service
from backend.app.validation.schemas import (
    ValidationError,
    validate_customer_id,
    validate_customer_name,
    validate_ticket_id,
    validate_ticket_issue,
    validate_ticket_status,
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
    def list_tickets(token: str, customer_id: int, status: str | None = None) -> dict:
        """List support tickets for a customer, optionally filtered by status."""

        try:
            customer_id = validate_customer_id(customer_id)
            if status is not None:
                status = validate_ticket_status(status)
        except ValidationError as error:
            return {"error": str(error)}

        user, auth_error = authorize_customer(token, customer_id)
        if auth_error:
            return auth_error

        return ticket_service.list_tickets(
            customer_id, user["customer_id"], user["role"], status=status
        )

    @mcp.tool()
    def get_ticket(token: str, ticket_id: int) -> dict:
        """Get one support ticket by id, if the caller is allowed to see it."""

        try:
            ticket_id = validate_ticket_id(ticket_id)
        except ValidationError as error:
            return {"error": str(error)}

        user = verify_token(token)
        if user is None:
            return {"error": "Invalid or expired token"}

        return ticket_service.get_ticket(ticket_id, user["customer_id"], user["role"])
