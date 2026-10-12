import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, Topic, User
from app.utils.security import get_password_hash


@pytest.fixture
def db():
    """Create an isolated database shared with TestClient's worker thread."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        with testing_session() as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def test_user(db):
    user = User(
        name="Test Student",
        email="student@example.com",
        hashed_password=get_password_hash("test-password-123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "test-password-123"},
    )
    assert response.status_code == 200, response.text
    token = response.json()
    assert token["token_type"] == "bearer"
    assert token["access_token"]
    return {"Authorization": f"Bearer {token['access_token']}"}


@pytest.fixture
def topic(db):
    topic = Topic(name="Anatomy", description="Base topic for game tests")
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic
