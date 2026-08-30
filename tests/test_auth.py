from fastapi.testclient import TestClient
from backend.app.api_main import app

client = TestClient(app)


def test_login_success():
    response = client.post(
        "/auth/login",
        json={
            "email": "fares@example.com",
            "password": "1234",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "token" in data
    assert data["customer_id"] == 1
    assert data["role"] == "admin"


def test_login_wrong_password():
    response = client.post(
        "/auth/login",
        json={
            "email": "fares@example.com",
            "password": "wrong",
        },
    )

    assert response.status_code == 401