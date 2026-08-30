from backend.app.auth.jwt import verify_token


def authorize_customer(token: str, customer_id: int) -> tuple[dict | None, dict | None]:
    user = verify_token(token)

    if user is None:
        return None, {"error": "Invalid or expired token"}

    if user["role"] == "admin" or user["customer_id"] == customer_id:
        return user, None

    return None, {"error": "Not authorized"}


def authorize_admin(token: str) -> tuple[dict | None, dict | None]:
    user = verify_token(token)

    if user is None:
        return None, {"error": "Invalid or expired token"}

    if user["role"] != "admin":
        return None, {"error": "Admin access required"}

    return user, None
