from datetime import timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from app.models import AcademicEdition, GameSession, Subject, User, UserRole
from app.models.user_import import UserImport
from app.services import activation_mail, user_onboarding
from app.utils import auth_limits
from app.utils.identity import LETTERS
from app.utils.security import get_password_hash
from tools.assign_user_dni import assign

PASSWORD = "synthetic-password-ñ"


def dni(number):
    return f"{number:08d}" + LETTERS[number % 23]


def csv_data(*rows):
    return ("dni;nombre;correo\r\n" + "\r\n".join(";".join(row) for row in rows) + "\r\n").encode()


def student_csv(*rows):
    default_edition = ("DEMO", "2026-2027")
    return ("dni;nombre;correo;codigo_asignatura;anio_academico\r\n" + "\r\n".join(
        ";".join(row + default_edition if len(row) == 3 else row) for row in rows
    ) + "\r\n").encode()


def post_csv(client, target, action, headers, raw, proof=None, mode=None):
    fields = {}
    if proof is not None:
        fields["proof"] = proof
    if target == "alumnado" and mode is not None:
        fields["mode"] = mode
    return client.post(f"/user-imports/{target}/{action}", headers=headers, files={
        "file": ("test.csv", raw, "text/csv"),
    }, data=fields)


def login(client, username, password=PASSWORD):
    return client.post("/auth/login", data={"username": username, "password": password})


@pytest.fixture
def managers(db, client, monkeypatch):
    monkeypatch.setattr(auth_limits, "limits", auth_limits.AuthLimits())
    sent = []

    def deliver(invitations, ttl):
        sent.extend((invitation, ttl) for invitation in invitations)
        return {invitation.user_id for invitation in invitations}

    monkeypatch.setattr(activation_mail, "send_invitations", deliver)
    subject = Subject(name="Asignatura de prueba", code="DEMO")
    db.add(subject)
    db.flush()
    db.add(AcademicEdition(subject_id=subject.id, academic_year="2026-2027"))
    headers = {}
    for n, role in enumerate((UserRole.ADMIN, UserRole.TEACHER, UserRole.STUDENT), 10):
        user = User(dni=dni(n), name=role.value, email=f"{role.value}@example.com",
                    hashed_password=get_password_hash(PASSWORD), role=role)
        db.add(user)
        db.commit()
        token = login(client, user.dni).json()["access_token"]
        headers[role.value] = {"Authorization": "Bearer " + token}
    return headers, sent


def test_roles_and_template(client, managers):
    headers, _ = managers
    for target, allowed in (("alumnado", "teacher"), ("profesorado", "admin")):
        row = (dni(41), "Example user", "new-user@example.com")
        raw = student_csv(row) if target == "alumnado" else csv_data(row)
        path = f"/user-imports/{target}"
        assert client.get(path + "/template").status_code == 401
        for role, auth in headers.items():
            expected = 200 if role == allowed else 403
            template = client.get(path + "/template", headers=auth)
            assert template.status_code == expected
            assert client.get(path + "/pending", headers=auth).status_code == expected
            assert post_csv(client, target, "validate", auth, raw).status_code == expected
            if role != allowed:
                assert post_csv(client, target, "confirm", auth, raw, "irrelevant").status_code == 403
                assert client.post(path + "/pending/11111111-1111-4111-8111-111111111111/resend", headers=auth).status_code == 403
        template = client.get(path + "/template", headers=headers[allowed]).text.lstrip("\ufeff").strip()
        assert template == raw.decode().splitlines()[0]
        with_role = raw.replace(b"dni;nombre;correo", b"dni;nombre;correo;rol")
        assert post_csv(client, target, "validate", headers[allowed], with_role).status_code == 422


@pytest.mark.parametrize("target,actor,role", [("alumnado", "teacher", UserRole.STUDENT), ("profesorado", "admin", UserRole.TEACHER)])
def test_confirm_once_and_activate(client, db, managers, target, actor, role):
    headers, mailbox = managers
    auth = headers[actor]
    n = dni(42)
    row = (n[:8] + "-" + n[-1].lower(), "  Ana  ", "ANA@example.com")
    raw = student_csv(row) if target == "alumnado" else csv_data(row)
    validated = post_csv(client, target, "validate", auth, raw).json()
    assert validated["valid"] == 1 and validated["errors"] == []
    assert n not in str(validated["preview"])
    assert db.scalar(select(User).where(User.dni == n)) is None
    assert post_csv(client, target, "confirm", auth, raw + b"\n", validated["proof"]).status_code == 422
    first = post_csv(client, target, "confirm", auth, raw, validated["proof"])
    extra = {"enrolled": 1, "already_enrolled": 0} if target == "alumnado" else {}
    assert first.json() == {"count": 1, "sent": 1, "replayed": False, **extra}
    replay = post_csv(client, target, "confirm", auth, raw, validated["proof"])
    assert replay.json() == {"count": 1, "sent": None, "replayed": True, **extra}
    assert len(mailbox) == 1 and len(db.scalars(select(UserImport)).all()) == 1
    user = db.scalar(select(User).where(User.dni == n))
    user_id = user.id
    assert user.role == role and user.name == "Ana" and user.email == "ana@example.com"
    invitation, hours = mailbox[0]
    assert hours == 24 and user.activation_hash != invitation.code
    assert login(client, n).status_code == 401 and user.hashed_password is None
    assert client.get("/auth/activate", params={"code": invitation.code}).status_code == 405
    bad = client.post("/auth/activate", json={"code": invitation.code, "password": "short"})
    assert bad.status_code == 422 and invitation.code not in bad.text
    body = {"code": invitation.code, "password": PASSWORD}
    assert client.post("/auth/activate", json=body).status_code == 200
    assert client.post("/auth/activate", json=body).status_code == 400
    db.refresh(user)
    assert user.activation_hash is None and user.id == user_id
    authenticated = login(client, n[:8] + " " + n[-1].lower())
    assert authenticated.status_code == 200
    session = {"Authorization": "Bearer " + authenticated.json()["access_token"]}
    assert login(client, user.email).status_code == 401
    assert client.post("/auth/me/password", headers=session, json={
        "current_password": PASSWORD, "new_password": "Synthetic changed", "confirmation": "Synthetic changed",
    }).status_code == 200
    assert login(client, n).status_code == 401
    assert login(client, n, "Synthetic changed").status_code == 200


def test_preview_errors_and_existing_accounts_are_unchanged(db, client, managers):
    headers, mailbox = managers
    existing = db.scalar(select(User).where(User.email == "admin@example.com"))
    identity = (existing.dni, existing.email, existing.role, existing.hashed_password)
    raw = student_csv(
        (dni(41), "", "invalid"),
        (dni(40), "First", "duplicate@example.com"),
        (dni(40), "Second", "DUPLICATE@example.com"),
        (existing.dni, "Conflict", "ADMIN@example.com"),
    )
    result = post_csv(client, "alumnado", "validate", headers["teacher"], raw).json()
    assert result["valid"] == 0 and result["proof"] is None
    assert {error["row"] for error in result["errors"]} == {2, 3, 4, 5}
    assert result["errors"][-1]["field"] == "rol"
    assert sum("duplicada" in error["message"] for error in result["errors"]) == 2
    assert (existing.dni, existing.email, existing.role, existing.hashed_password) == identity
    assert mailbox == []


def test_failed_delivery_expiry_and_resend(client, db, managers, monkeypatch):
    headers, mailbox = managers
    failed = Mock(return_value=set())
    raw = student_csv((dni(71), "Example", "failed-delivery@example.com"))
    validate = post_csv(client, "alumnado", "validate", headers["teacher"], raw).json()
    with monkeypatch.context() as patch:
        patch.setattr(activation_mail, "send_invitations", failed)
        assert post_csv(client, "alumnado", "confirm", headers["teacher"], raw, validate["proof"]).json()["sent"] == 0
    saved = db.scalar(select(User).where(User.dni == dni(71)))
    initial = failed.call_args.args[0][0].code
    pending = f"/user-imports/alumnado/pending/{saved.id}/resend"
    assert client.post(pending, headers=headers["teacher"]).status_code == 429
    saved.invitation_attempted_at = user_onboarding.now() - timedelta(minutes=5)
    db.commit()
    assert client.post(pending, headers=headers["teacher"]).json() == {"sent": True}
    code = mailbox[0][0].code
    assert code != initial
    assert client.post("/auth/activate", json={"code": initial, "password": PASSWORD}).status_code == 400
    saved.activation_expires_at = user_onboarding.now() - timedelta(seconds=1)
    db.commit()
    assert client.post("/auth/activate", json={"code": code, "password": PASSWORD}).status_code == 400
    assert db.get(User, saved.id).hashed_password is None


def test_associate_legacy_account_preserves_history(client, db, test_user):
    test_user.dni = None
    previous_id, previous_hash = test_user.id, test_user.hashed_password
    history = GameSession(user_id=previous_id, topic_id=None, question_ids=[], score=0, is_completed=False,
                          content_context={"saved": "Original"})
    db.add(history)
    db.commit()
    assert login(client, test_user.email, "test-password-123").status_code == 401
    assign(db, previous_id, dni(43))
    assert login(client, dni(43), "test-password-123").status_code == 200
    db.refresh(history)
    assert history.user_id == previous_id and history.content_context == {"saved": "Original"}
    assert test_user.hashed_password == previous_hash
    with pytest.raises(ValueError):
        assign(db, previous_id, dni(44))
