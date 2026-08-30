from fastapi.testclient import TestClient

from backend.app.api_main import app

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