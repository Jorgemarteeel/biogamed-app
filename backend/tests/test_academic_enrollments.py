import pytest
from sqlalchemy import func, select

from app.models import AcademicEdition, Enrollment, GameSession, Subject, User, UserRole
from test_user_onboarding import PASSWORD, dni, login, managers, post_csv, student_csv


def preview(client, auth, raw, mode=None):
    response = post_csv(client, "alumnado", "validate", auth, raw, mode=mode)
    assert response.status_code == 200
    return response.json()


def confirm(client, auth, raw, proof, mode=None):
    return post_csv(client, "alumnado", "confirm", auth, raw, proof, mode=mode)


def create(client, auth, subject_id, year, code=None):
    return client.post("/academic-editions", headers=auth, json={
        "subject_id": subject_id, "academic_year": year, "subject_code": code,
    })


def test_edition_catalog_has_unique_code_and_existing_subject(client, db, managers):
    roles, _ = managers
    teacher = roles["teacher"]
    subject = Subject(name="Segunda asignatura")
    db.add(subject)
    db.commit()
    assert client.get("/academic-editions").status_code == 401
    for role in ("student", "admin"):
        assert client.get("/academic-editions/subjects", headers=roles[role]).status_code == 403
        assert create(client, roles[role], subject.id, "2026-2027", "SECOND").status_code == 403
    assert create(client, teacher, subject.id, "2026-2027").status_code == 422
    assert create(client, teacher, subject.id, "2026-2028", "SECOND").status_code == 422
    assert create(client, teacher, subject.id, "2026-2027", "DEMO").status_code == 409
    assert create(client, teacher, 900, "2026-2027", "UNKNOWN").status_code == 404
    assert create(client, teacher, subject.id, "2026-2027", "second").json()["subject_code"] == "SECOND"
    assert create(client, teacher, subject.id, "2026-2027").status_code == 409
    assert create(client, teacher, subject.id, "2027-2028", "CHANGED").status_code == 409
    assert create(client, teacher, subject.id, "2027-2028").status_code == 201
    items = client.get("/academic-editions", headers=teacher).json()["items"]
    assert sum(row["subject_code"] == "SECOND" for row in items) == 2
    assert db.scalar(select(func.count()).select_from(Subject)) == 2


def test_one_new_account_and_invitation_across_editions(client, db, managers):
    roles, mailbox = managers
    teacher = roles["teacher"]
    subject = Subject(name="Segunda asignatura", code="SECOND")
    db.add(subject)
    db.flush()
    db.add(AcademicEdition(subject_id=subject.id, academic_year="2026-2027"))
    db.commit()
    row = (dni(91), "Nueva alumna", "new-91@example.com")
    raw = student_csv(row, row + ("SECOND", "2026-2027"))
    validated = preview(client, teacher, raw)
    assert [item["action"] for item in validated["preview"]] == ["new_account", "new_account"]
    assert validated["summary"] == {"new_accounts": 1, "new_enrollments": 2, "year_changes": 0}
    assert [item["account_row"] for item in validated["preview"]] == [2, 2]
    assert len({item["edition_id"] for item in validated["preview"]}) == 2
    assert confirm(client, teacher, raw, validated["proof"]).json() == {
        "count": 1, "enrolled": 2, "already_enrolled": 0, "sent": 1, "replayed": False,
    }
    user = db.scalar(select(User).where(User.dni == row[0]))
    assert user.hashed_password is None and user.activation_hash
    enrollments = db.scalars(select(Enrollment).where(Enrollment.student_id == user.id)).all()
    assert len(enrollments) == 2 and all(item.play_enabled for item in enrollments)
    assert len(mailbox) == 1
    assert confirm(client, teacher, raw, validated["proof"]).json()["replayed"]
    assert len(mailbox) == 1


def test_repeater_and_existing_enrollment_keep_identity_history_and_enabled_year(client, db, managers):
    roles, mailbox = managers
    teacher = roles["teacher"]
    student = db.scalar(select(User).where(User.role == UserRole.STUDENT))
    before = (student.id, student.name, student.dni, student.email, student.role, student.hashed_password,
              student.activation_hash, student.auth_version)
    first = db.scalar(select(AcademicEdition))
    newer = AcademicEdition(subject_id=first.subject_id, academic_year="2027-2028")
    db.add_all([
        newer,
        Enrollment(student_id=student.id, edition_id=first.id, subject_id=first.subject_id, play_enabled=True),
        GameSession(user_id=student.id, question_ids=[], score=3, is_completed=True, content_context={"original": True}),
    ])
    db.commit()
    row = (student.dni, "Otro nombre", student.email.upper())
    raw = student_csv(row + ("demo", "2027-2028"))
    validated = preview(client, teacher, raw)
    assert [item["action"] for item in validated["preview"]] == ["new_enrollment"]
    assert confirm(client, teacher, raw, validated["proof"]).json() == {
        "count": 0, "enrolled": 1, "already_enrolled": 0, "sent": 0, "replayed": False,
    }
    db.refresh(student)
    assert (student.id, student.name, student.dni, student.email, student.role, student.hashed_password,
            student.activation_hash, student.auth_version) == before
    assert db.scalar(select(GameSession).where(GameSession.user_id == student.id)).content_context == {"original": True}
    roster = "/academic-editions/" + str(newer.id) + "/enrollments"
    assert client.get(roster, headers=teacher).json()["items"][0]["enabled_year"] == "2027-2028"
    roster = "/academic-editions/" + str(first.id) + "/enrollments"
    enable = roster + "/" + str(student.id) + "/play"
    assert client.put(enable, headers=roles["student"], json={"expected_edition_id": newer.id}).status_code == 403
    assert client.put(enable, headers=teacher, json={"expected_edition_id": None}).status_code == 409
    assert client.put(enable, headers=teacher, json={"expected_edition_id": newer.id}).status_code == 200
    db.expire_all()
    assert db.get(Enrollment, (student.id, first.id)).play_enabled
    assert not db.get(Enrollment, (student.id, newer.id)).play_enabled
    # Another teacher's new import may see both rows, but does not change their eligibility.
    assert [item["action"] for item in preview(client, teacher, raw)["preview"]] == [
        "existing_enrollment",
    ]
    assert mailbox == []


def test_conflicts_unknown_edition_and_revalidation_leave_batch_unchanged(client, db, managers):
    roles, mailbox = managers
    teacher = roles["teacher"]
    student = db.scalar(select(User).where(User.role == UserRole.STUDENT))
    teacher_account = db.scalar(select(User).where(User.role == UserRole.TEACHER))
    raw = student_csv(
        (student.dni, "Conflicto", teacher_account.email),
        (teacher_account.dni, "Rol incompatible", teacher_account.email),
        (dni(92), "Sin edición", "new-92@example.com", "DEMO", "2030-2031"),
        (dni(93), "Código mal escrito", "new-93@example.com", "DEMO-TYPO", "2026-2027"),
    )
    result = preview(client, teacher, raw)
    assert not result["proof"] and not result["valid"]
    fields_by_row = {row: {issue["field"] for issue in result["errors"] if issue["row"] == row}
                     for row in range(2, 6)}
    assert fields_by_row == {
        2: {"dni / correo"}, 3: {"dni / correo", "rol"},
        4: {"codigo_asignatura / anio_academico"}, 5: {"codigo_asignatura / anio_academico"},
    }
    raw = student_csv((dni(92), "Nueva", "new-92@example.com"), (dni(93), "Otra", "new-93@example.com"))
    validated = preview(client, teacher, raw)
    db.add(User(dni=dni(95), name="Intercalada", email="new-93@example.com", role=UserRole.STUDENT))
    db.commit()
    response = confirm(client, teacher, raw, validated["proof"])
    assert response.status_code == 409 and response.json()["detail"]["errors"][0]["row"] == 3
    assert db.scalar(select(User).where(User.dni == dni(92))) is None
    assert db.scalar(select(func.count()).select_from(Enrollment)) == 0
    assert db.scalar(select(func.count()).select_from(AcademicEdition)) == 1
    assert mailbox == []


def other_years(db):
    subject = db.scalar(select(Subject).where(Subject.code == "DEMO"))
    db.add_all([AcademicEdition(subject_id=subject.id, academic_year=year)
                for year in ("2024-2025", "2025-2026")])
    db.commit()


def enabled_year(db, student):
    return db.scalar(select(AcademicEdition.academic_year)
                     .join(Enrollment, Enrollment.edition_id == AcademicEdition.id)
                     .where(Enrollment.student_id == student.id, Enrollment.play_enabled.is_(True)))


def test_switch_import_keeps_account_password_history_and_invitation(client, db, managers):
    roles, mailbox = managers
    auth = roles["teacher"]
    other_years(db)
    row = (dni(81), "Nueva alumna", "student81@example.com")
    initial = student_csv(row + ("DEMO", "2025-2026"))
    current = student_csv(row)

    first = preview(client, auth, initial)
    assert first["preview"][0]["previous_year"] is None
    assert first["preview"][0]["enabled_year"] == "2025-2026"
    assert confirm(client, auth, initial, first["proof"]).json()["sent"] == 1
    assert confirm(client, auth, initial, first["proof"]).json()["replayed"]
    assert client.post("/auth/activate", json={"code": mailbox[0][0].code, "password": PASSWORD}).status_code == 200
    student = db.scalar(select(User).where(User.dni == row[0]))
    student_id, password_hash = student.id, student.hashed_password
    db.add(GameSession(user_id=student.id, question_ids=[], score=9, is_completed=True,
                       content_context={"history": "preserved"}))
    db.commit()

    replacement = preview(client, auth, current)
    assert replacement["summary"] == {"new_accounts": 0, "new_enrollments": 1, "year_changes": 1}
    assert replacement["preview"][0]["previous_edition_id"] == first["preview"][0]["edition_id"]
    assert (replacement["preview"][0]["previous_year"], replacement["preview"][0]["enabled_year"]) == (
        "2025-2026", "2026-2027",
    )
    assert confirm(client, auth, current, replacement["proof"]).json() == {
        "count": 0, "enrolled": 1, "already_enrolled": 0, "sent": 0, "replayed": False,
    }
    assert enabled_year(db, student) == "2026-2027"
    for key, expected_enabled in [("previous_edition_id", False), ("edition_id", True)]:
        edition_id = replacement["preview"][0][key]
        roster = client.get(f"/academic-editions/{edition_id}/enrollments", headers=auth).json()
        assert roster["edition"]["id"] == edition_id
        assert roster["items"][0]["id"] == str(student_id)
        assert roster["items"][0]["play_enabled"] is expected_enabled
    # A stale retry cannot switch back after another import, but a fresh preview of
    # the same file can intentionally enable a destination that already exists.
    assert confirm(client, auth, initial, first["proof"]).json()["replayed"]
    assert enabled_year(db, student) == "2026-2027"
    restore = preview(client, auth, initial)
    assert restore["preview"][0]["action"] == "existing_enrollment"
    assert confirm(client, auth, initial, restore["proof"]).json()["already_enrolled"] == 1
    assert enabled_year(db, student) == "2025-2026"

    db.refresh(student)
    assert student.id == student_id and student.hashed_password == password_hash and student.activation_hash is None
    assert login(client, row[0]).status_code == 200
    match = db.scalar(select(GameSession).where(GameSession.user_id == student_id))
    assert match.score == 9 and match.content_context == {"history": "preserved"}
    assert db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.student_id == student_id)) == 2
    assert len(mailbox) == 1


def test_existing_inactive_enrollment_needs_confirmation_and_noop_does_not(client, db, managers):
    roles, mailbox = managers
    auth = roles["teacher"]
    student = db.scalar(select(User).where(User.role == UserRole.STUDENT))
    edition = db.scalar(select(AcademicEdition))
    db.add(Enrollment(student_id=student.id, edition_id=edition.id, subject_id=edition.subject_id, play_enabled=False))
    db.commit()
    raw = student_csv((student.dni, student.name, student.email))
    for action in ("validate", "confirm"):
        assert post_csv(client, "alumnado", action, auth, raw, proof="old", mode="historical").status_code == 422
    validated = preview(client, auth, raw)
    assert validated["summary"] == {"new_accounts": 0, "new_enrollments": 0, "year_changes": 0}
    assert validated["has_changes"] is True
    assert validated["preview"][0]["previous_year"] is None
    assert confirm(client, auth, raw, validated["proof"]).json()["sent"] == 0
    assert enabled_year(db, student) == "2026-2027"
    unchanged = preview(client, auth, raw)
    assert unchanged["has_changes"] is False
    assert mailbox == []


@pytest.mark.parametrize("reverse", [True, False])
def test_two_enabled_years_are_rejected_in_both_orders(client, db, managers, reverse):
    roles, mailbox = managers
    auth = roles["teacher"]
    other_years(db)
    row = (dni(83), "Dos años", "student83@example.com", "DEMO")
    rows = [row + ("2025-2026",), row + ("2026-2027",)]
    raw = student_csv(*(rows[::-1] if reverse else rows))
    result = preview(client, auth, raw)
    assert result["proof"] is None and result["valid"] == 0
    assert [(error["row"], error["field"]) for error in result["errors"]] == [(2, "anio_academico"), (3, "anio_academico")]
    assert confirm(client, auth, raw, "invalid").status_code == 422
    assert db.scalar(select(func.count()).select_from(Enrollment)) == 0
    assert not mailbox


def test_enable_rejects_a_change_not_shown_in_preview(client, db, managers):
    roles, _ = managers
    auth = roles["teacher"]
    other_years(db)
    row = (dni(84), "Cambio simultáneo", "student84@example.com", "DEMO")
    oldest = student_csv(row + ("2024-2025",))
    previous = student_csv(row + ("2025-2026",))
    latest = student_csv(row + ("2026-2027",))
    assert confirm(client, auth, oldest, preview(client, auth, oldest)["proof"]).status_code == 200
    stale = preview(client, auth, latest)
    assert stale["preview"][0]["previous_year"] == "2024-2025"
    assert confirm(client, auth, previous, preview(client, auth, previous)["proof"]).status_code == 200
    assert confirm(client, auth, latest, stale["proof"]).status_code == 409
    student = db.scalar(select(User).where(User.dni == row[0]))
    assert enabled_year(db, student) == "2025-2026"
