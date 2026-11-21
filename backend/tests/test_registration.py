from sqlalchemy import select

from app.models import User


def test_public_registration_is_disabled(client, db):
    payload = {"name": "Synthetic", "email": "public-registration@example.com", "password": "example-password"}
    for body in (payload, {**payload, "role": "admin"}, {}):
        assert client.post("/auth/register", json=body).status_code == 410
    assert db.scalar(select(User).where(User.email == payload["email"])) is None
