from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.auth.jwt import verify_token


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    user = verify_token(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return user