from backend.app.services import customer_service
from backend.app.validation.schemas import ValidationError, validate_email, validate_password


def register_auth_tools(mcp) -> None:
    @mcp.tool()
    def login(email: str, password: str) -> dict:
        """Authenticate a customer and return a one-hour JWT."""

        try:
            email = validate_email(email)
            password = validate_password(password)
        except ValidationError as error:
            return {"error": str(error)}

        return customer_service.login(email, password)
