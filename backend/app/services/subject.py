from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subject
from app.schemas.subject import SubjectCreate


def get_subjects(db: Session, skip: int = 0, limit: int = 100) -> list[Subject]:
    statement = select(Subject).order_by(Subject.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_subject(db: Session, subject: SubjectCreate) -> Subject:
    db_subject = Subject(**subject.model_dump())
    db.add(db_subject)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(db_subject)
    return db_subject
