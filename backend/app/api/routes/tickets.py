from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_current_user
from backend.app.services.ticket_service import create_ticket, list_tickets


router = APIRouter(
    prefix="/tickets",
    tags=["tickets"],
)


class TicketRequest(BaseModel):
    issue: str


@router.get("")
def get_tickets(user: dict = Depends(get_current_user)):
    return list_tickets(
        customer_id=user["customer_id"],
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )


@router.post("")
def create_new_ticket(
    request: TicketRequest,
    user: dict = Depends(get_current_user),
):
    result = create_ticket(
        customer_id=user["customer_id"],
        issue=request.issue,
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"],
        )

    return result