from fastapi.testclient import TestClient

from backend.app.api_main import app
from backend.app.database.repositories import ticket_repository

client = TestClient(app)


def get_token():
    response = client.post(
        "/auth/login",
        json={
            "email": "fares@example.com",
            "password": "1234",
        },
    )

    assert response.status_code == 200
    return response.json()["token"]


def get_customer_session():
    response = client.post(
        "/auth/login",
        json={
            "email": "ali@example.com",
            "password": "5678",
        },
    )

    assert response.status_code == 200
    return response.json()


def test_create_ticket():
    token = get_token()

    response = client.post(
        "/tickets",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "issue": "My account is locked"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["issue"] == "My account is locked"
    assert data["status"] == "open"


def test_list_tickets():
    token = get_token()

    response = client.get(
        "/tickets",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert "tickets" in response.json()


def test_list_tickets_normalizes_status_values():
    response = client.get(
        "/tickets",
        headers={"Authorization": f"Bearer {get_token()}"},
    )

    assert response.status_code == 200
    assert all(
        ticket["status"] in {"open", "closed"}
        for ticket in response.json()["tickets"]
    )


def test_list_tickets_status_filter():
    response = client.get(
        "/tickets?status=open",
        headers={"Authorization": f"Bearer {get_token()}"},
    )

    assert response.status_code == 200
    assert all(t["status"] == "open" for t in response.json()["tickets"])


def test_get_one_ticket_own_and_foreign():
    session = get_customer_session()
    ticket_id = ticket_repository.create(session["customer_id"], "Ticket for the get-one test")

    own = client.get(
        f"/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert own.status_code == 200
    assert own.json()["ticket_id"] == ticket_id

    missing = client.get(
        "/tickets/99999999",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert missing.status_code == 404


def test_customer_lists_only_their_own_tickets():
    session = get_customer_session()
    customer_ticket_id = ticket_repository.create(
        session["customer_id"],
        "Ticket used to verify customer visibility",
    )

    response = client.get(
        "/tickets",
        headers={"Authorization": f"Bearer {session['token']}"},
    )

    assert response.status_code == 200
    assert any(
        ticket["ticket_id"] == customer_ticket_id
        for ticket in response.json()["tickets"]
    )
    assert all(
        ticket["customer_id"] == session["customer_id"]
        for ticket in response.json()["tickets"]
    )


def test_admin_lists_tickets_for_all_customers():
    customer_session = get_customer_session()
    customer_ticket_id = ticket_repository.create(
        customer_session["customer_id"],
        "Ticket visible to an administrator",
    )

    response = client.get(
        "/tickets",
        headers={"Authorization": f"Bearer {get_token()}"},
    )

    assert response.status_code == 200
    assert any(
        ticket["ticket_id"] == customer_ticket_id
        and ticket["customer_id"] == customer_session["customer_id"]
        for ticket in response.json()["tickets"]
    )


def test_admin_can_close_and_reopen_ticket():
    token = get_token()
    create_response = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={"issue": "Ticket status can be changed by an administrator"},
    )
    assert create_response.status_code == 200
    ticket_id = create_response.json()["ticket_id"]

    close_response = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "closed"},
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"

    open_response = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "open"},
    )
    assert open_response.status_code == 200
    assert open_response.json()["status"] == "open"


def test_customer_cannot_change_ticket_status():
    session = get_customer_session()

    response = client.patch(
        "/tickets/1/status",
        headers={"Authorization": f"Bearer {session['token']}"},
        json={"status": "closed"},
    )

    assert response.status_code == 403
