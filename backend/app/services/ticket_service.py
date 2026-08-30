from backend.app.database.repositories import (
    audit_repository,
    customer_repository,
    ticket_repository,
)


def create_ticket(
    customer_id: int,
    issue: str,
    actor_customer_id: int,
    actor_role: str,
) -> dict:
    audit_repository.log_action(actor_customer_id, actor_role, "create_ticket")
    customer = customer_repository.find_status_by_id(customer_id)

    if customer is None:
        return {"error": "Customer not found"}

    if customer[0] != "active":
        return {"error": "Inactive customers cannot create support tickets"}

    ticket_id = ticket_repository.create(customer_id, issue)
    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "issue": issue,
        "status": "open",
    }


def list_tickets(customer_id: int, actor_customer_id: int, actor_role: str) -> dict:
    audit_repository.log_action(actor_customer_id, actor_role, "list_tickets")
    tickets = (
        ticket_repository.find_all()
        if actor_role == "admin"
        else ticket_repository.find_by_customer_id(customer_id)
    )

    return {
        "tickets": [
            {
                "ticket_id": ticket[0],
                "customer_id": ticket[1],
                "issue": ticket[2],
                "status": ticket[3].lower(),
            }
            for ticket in tickets
        ]
    }


def update_ticket_status(
    ticket_id: int,
    status: str,
    actor_customer_id: int,
    actor_role: str,
) -> dict:
    if actor_role != "admin":
        return {"error": "Admin access required"}

    audit_repository.log_action(actor_customer_id, actor_role, "update_ticket_status")
    ticket = ticket_repository.update_status(ticket_id, status)

    if ticket is None:
        return {"error": "Ticket not found"}

    return {
        "ticket_id": ticket[0],
        "customer_id": ticket[1],
        "issue": ticket[2],
        "status": ticket[3].lower(),
    }
