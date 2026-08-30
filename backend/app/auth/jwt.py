from datetime import datetime, timedelta, timezone

import jwt

from backend.app.config import JWT_SECRET


JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY = timedelta(hours=1)


def create_token(customer_id: int, role: str) -> str:
    payload = {
        "customer_id": customer_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "customer_id": payload["customer_id"],
            "role": payload["role"],
        }
    except (jwt.InvalidTokenError, KeyError, TypeError):
        return None
