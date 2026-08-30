import re


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ValidationError(ValueError):
    """Raised when an MCP tool receives invalid input."""


def validate_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Invalid email")

    email = email.strip()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValidationError("Invalid email")

    return email


def validate_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValidationError("Password is required")

    return password


def validate_customer_id(customer_id: int) -> int:
    if isinstance(customer_id, bool) or not isinstance(customer_id, int) or customer_id <= 0:
        raise ValidationError("customer_id must be greater than 0")

    return customer_id


def validate_customer_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Customer name is required")

    return name.strip()


def validate_ticket_issue(issue: str) -> str:
    if not isinstance(issue, str):
        raise ValidationError("Ticket issue must be between 5 and 1000 characters")

    issue = issue.strip()
    if len(issue) < 5 or len(issue) > 1000:
        raise ValidationError("Ticket issue must be between 5 and 1000 characters")

    return issue
