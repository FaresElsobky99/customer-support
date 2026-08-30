import bcrypt

from backend.app.auth.jwt import create_token
from backend.app.database.repositories import audit_repository, customer_repository


def login(email: str, password: str) -> dict:
    row = customer_repository.find_login_by_email(email)

    if row is None:
        return {"error": "Invalid credentials"}

    customer_id, stored_password, role = row
    stored_password_bytes = (
        stored_password.encode() if isinstance(stored_password, str) else stored_password
    )

    if not bcrypt.checkpw(password.encode(), stored_password_bytes):
        return {"error": "Invalid credentials"}

    return {
        "token": create_token(customer_id, role),
        "customer_id": customer_id,
        "role": role,
    }


def get_customer(customer_id: int, actor_customer_id: int, actor_role: str) -> dict:
    audit_repository.log_action(actor_customer_id, actor_role, "get_customer")
    row = customer_repository.find_by_id(customer_id)

    if row is None:
        return {"error": "Customer not found"}

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "status": row[3],
    }


def list_all_customers(actor_customer_id: int, actor_role: str) -> dict:
    audit_repository.log_action(actor_customer_id, actor_role, "list_all_customers")
    rows = customer_repository.find_all()

    return {
        "customers": [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "status": row[3],
                "role": row[4],
            }
            for row in rows
        ]
    }
