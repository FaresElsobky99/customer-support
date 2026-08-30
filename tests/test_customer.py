from fastapi.testclient import TestClient

from backend.app.api_main import app

client = TestClient(app)


def get_admin_token():
    response = client.post(
        "/auth/login",
        json={
            "email": "fares@example.com",
            "password": "1234",
        },
    )
    assert response.status_code == 200

    return response.json()["token"]

def get_non_admin_token():
    # First, create a non-admin user
    response = client.post(
        "/auth/login",
        json={
            "email": "ali@example.com",
            "password": "5678",
        },
    )   
    assert response.status_code == 200
    return response.json()["token"]



def test_get_me_without_token():
    response = client.get("/customers/me")

    assert response.status_code == 401


def test_get_me_with_token():
    token = get_admin_token()

    response = client.get(
        "/customers/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["email"] == "fares@example.com"

def test_admin_can_list_customers():
    token = get_admin_token()

    response = client.get(
        "/customers",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert "customers" in response.json()


def test_non_admin_cannot_list_customers():
    token = get_non_admin_token()

    response = client.get(
        "/customers",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )


    assert response.status_code == 403


