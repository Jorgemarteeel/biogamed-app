from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AcademicEdition, Enrollment, GameSession, Subject, User, UserRole
from app.services import activation_mail, user_onboarding
from migration_fixtures import origin_schema
from test_pasapalabra_postgres import postgres
from test_user_onboarding import dni, student_csv


@pytest.mark.parametrize("same_actor", [True, False])
def test_concurrent_confirmations_share_account_enrollment_and_invitation(postgres, monkeypatch, same_actor):
    mailbox = []

    def deliver(invitations, ttl):
        mailbox.extend(invitations)
        return {invitation.user_id for invitation in invitations}

    monkeypatch.setattr(activation_mail, "send_invitations", deliver)
    raw = student_csv((dni(98), "Race", "race-enrollment@example.com"))
    with Session(postgres) as db:
        teachers = [User(name=str(i), email=f"teacher-{i}@example.com", hashed_password="fixture",
                         role=UserRole.TEACHER) for i in range(2)]
        subject = Subject(name="Race", code="DEMO")
        db.add_all([subject, *teachers])
        db.flush()
        db.add(AcademicEdition(subject_id=subject.id, academic_year="2026-2027"))
        db.commit()
        operations = [(teacher.id, user_onboarding.preview(db, teacher, "alumnado", raw)["proof"]) for teacher in teachers]
        if same_actor:
            operations[1] = operations[0]
    barrier = Barrier(2)

    def worker(operation):
        actor_id, proof = operation
        with Session(postgres) as db:
            actor = db.get(User, actor_id)
            barrier.wait(timeout=10)
            try:
                return user_onboarding.confirm(db, actor, "alumnado", raw, proof)
            except HTTPException as error:
                return {"status": error.status_code}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, operations))
    assert len(mailbox) == 1
    assert sum(result.get("sent") or 0 for result in results) == 1
    if same_actor:
        assert sum(result["replayed"] for result in results) == 1
    else:
        assert sum(result.get("status") == 409 for result in results) == 1
    with Session(postgres) as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.dni == dni(98))) == 1
        assert db.scalar(select(func.count()).select_from(Enrollment)) == 1


def test_migration_preserves_previous_data_and_enforces_unique_enabled_edition(postgres):
    user_id = uuid4()
    with origin_schema(postgres, "04cf5b8ad91e") as engine:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id, name, email, hashed_password, role, auth_version) "
                "VALUES (:id, 'Previous', 'previous@example.com', 'stored-hash', 'STUDENT', 1)"
            ), {"id": user_id})
            connection.execute(text(
                "INSERT INTO game_engine_sessions (user_id, score, is_completed, created_at, question_ids) "
                "VALUES (:id, 3, true, now(), '[]')"
            ), {"id": user_id})
            connection.execute(text("INSERT INTO subjects (name) VALUES ('Previous subject')"))
        with patch("app.database.engine", engine):
            command.upgrade(Config("alembic.ini"), "head")
        with Session(engine) as db:
            assert db.get(User, user_id).hashed_password == "stored-hash"
            assert db.scalar(select(GameSession).where(GameSession.user_id == user_id)).score == 3
            subject = db.scalar(select(Subject))
            assert subject.name == "Previous subject" and subject.code is None
            assert db.scalar(select(func.count()).select_from(Enrollment)) == 0
            old = AcademicEdition(subject_id=subject.id, academic_year="2026-2027")
            new = AcademicEdition(subject_id=subject.id, academic_year="2027-2028")
            db.add_all([old, new])
            db.flush()
            db.add(Enrollment(student_id=user_id, edition_id=old.id, subject_id=subject.id, play_enabled=True))
            db.commit()
            db.add(Enrollment(student_id=user_id, edition_id=new.id, subject_id=subject.id, play_enabled=True))
            with pytest.raises(IntegrityError) as conflict:
                db.flush()
            assert "uq_enrollment_enabled_subject" in str(conflict.value)
            db.rollback()
            db.add(Enrollment(student_id=user_id, edition_id=new.id, subject_id=subject.id + 100,
                              play_enabled=False))
            with pytest.raises(IntegrityError) as conflict:
                db.flush()
            assert "fk_enrollment_edition_subject" in str(conflict.value)
