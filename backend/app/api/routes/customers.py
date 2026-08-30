from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import get_current_user
from backend.app.services.customer_service import (
    get_customer,
    list_all_customers,
)


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return get_customer(
        customer_id=user["customer_id"],
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )


@router.get("")
def get_all_customers(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return list_all_customers(
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )