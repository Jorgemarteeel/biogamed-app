from sqlalchemy import select

from app.models import User
from app.utils.security import verify_password


def test_registration_then_login_and_duplicate_email(client, db):
    payload = {"name": "Registration Test", "email": "register@example.com",
               "password": "registration-password-123"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "student"
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()
    user = db.scalar(select(User).where(User.email == payload["email"]))
    assert user.hashed_password != payload["password"]
    assert verify_password(payload["password"], user.hashed_password)
    login = client.post("/auth/login", data={
        "username": payload["email"], "password": payload["password"],
    })
    assert login.status_code == 200
    assert login.json()["access_token"]
    assert client.post("/auth/register", json=payload).status_code == 400
    assert len(list(db.scalars(select(User)))) == 1


def test_registration_rejects_invalid_input(client):
    response = client.post("/auth/register", json={
        "name": "Test", "email": "invalid", "password": "short",
    })
    assert response.status_code == 422
