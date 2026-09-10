from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_current_user
from backend.app.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_status,
)

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"],
)


class TicketRequest(BaseModel):
    issue: str


class TicketStatusRequest(BaseModel):
    status: Literal["open", "closed"]


@router.get("")
def get_tickets(user: dict = Depends(get_current_user), status: str | None = None):
    return list_tickets(
        customer_id=user["customer_id"],
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
        status=status,
    )


@router.get("/{ticket_id}")
def get_one_ticket(ticket_id: int, user: dict = Depends(get_current_user)):
    result = get_ticket(
        ticket_id=ticket_id,
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )

    if "error" in result:
        status_code = 404 if result["error"] == "Ticket not found" else 403
        raise HTTPException(status_code=status_code, detail=result["error"])

    return result


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


@router.patch("/{ticket_id}/status")
def change_ticket_status(
    ticket_id: int,
    request: TicketStatusRequest,
    user: dict = Depends(get_current_user),
):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    result = update_ticket_status(
        ticket_id=ticket_id,
        status=request.status,
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    return result
