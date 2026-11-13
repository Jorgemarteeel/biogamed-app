import os
import subprocess
import sys
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.utils.auth_limits import AuthLimits


@pytest.mark.parametrize("value", [None, "", "   ", "dev-only-change-this-secret-key-before-production"])
@pytest.mark.parametrize("module", ["app.main", "tools.bootstrap_admin"])
def test_startup_rejects_unsafe_secret(value, module):
    env = dict(os.environ)
    env.pop("SECRET_KEY", None)
    if value is not None:
        env["SECRET_KEY"] = value
    result = subprocess.run([sys.executable, "-c", f"import {module}"], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "Configure an explicit" in result.stderr


def test_valid_secret_starts_backend():
    env = dict(os.environ, SECRET_KEY="isolated-test-explicit-key-only-32bytes")
    result = subprocess.run([sys.executable, "-c", "import app.main; assert not app.main.app.debug"], env=env, capture_output=True)
    assert result.returncode == 0


def test_windows_separation_and_retry(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_LIMIT", "2")
    monkeypatch.setenv("AUTH_LOGIN_WINDOW_SECONDS", "10")
    now = [0.0]
    limiter = AuthLimits(clock=lambda: now[0])
    limiter.check("login", "peer-a"); limiter.check("login", "peer-a")
    now[0] = 0.5
    with pytest.raises(HTTPException) as error:
        limiter.check("login", "peer-a")
    assert error.value.status_code == 429 and error.value.headers["Retry-After"] == "10"
    limiter.check("register", "peer-a")
    limiter.check("login", "peer-b")
    now[0] = 10
    limiter.check("login", "peer-a")


@pytest.mark.parametrize("kind", ["login", "register"])
def test_limits_precede_hashing_and_ignore_headers(client, test_user, monkeypatch, kind):
    from app.utils import auth_limits
    from app.routers import auth
    monkeypatch.setenv("AUTH_LOGIN_LIMIT", "1")
    monkeypatch.setenv("AUTH_REGISTER_LIMIT", "1")
    monkeypatch.setattr(auth_limits, "limits", AuthLimits())
    if kind == "login":
        path = "/auth/login"
        payload = dict(data={"username": test_user.email, "password": "test-password-123"})
        assert client.post(path, **payload).status_code == 200
        costly = Mock(side_effect=AssertionError("must not hash"))
        monkeypatch.setattr(auth, "verify_password", costly)
    else:
        path = "/auth/register"
        payload = dict(json={"name": "Synthetic", "email": "synthetic@example.com", "password": "test-password-123"})
        assert client.post(path, **payload).status_code == 201
        costly = Mock(side_effect=AssertionError("must not hash"))
        monkeypatch.setattr(auth.user_service, "get_password_hash", costly)
    response = client.post(path, **payload, headers={"X-Forwarded-For": "198.51.100.123", "X-Real-IP": "203.0.113.10", "Forwarded": "for=198.51.100.123"})
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    costly.assert_not_called()


def test_bounded_state():
    limiter = AuthLimits(); limiter.capacity = 2
    for peer in ["a", "b", "c"]:
        limiter.check("login", peer)
    assert len(limiter.entries) == 2
