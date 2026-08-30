from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.customer_service import login as login_customer


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(request: LoginRequest):
    result = login_customer(
        request.email,
        request.password,
    )

    if "error" in result:
        raise HTTPException(
            status_code=401,
            detail=result["error"],
        )

    return result