from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ContentBlock, Subject
from app.schemas.content_block import ContentBlockCreate
from app.schemas.subject import SubjectCreate


def get_subjects(db: Session, skip: int = 0, limit: int = 100) -> list[Subject]:
    statement = select(Subject).order_by(Subject.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_subject(db: Session, subject_id: int) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(404, "La asignatura no existe.")
    return subject


def get_blocks(db: Session, subject_id: int, skip: int = 0, limit: int = 100) -> list[ContentBlock]:
    get_subject(db, subject_id)
    statement = (select(ContentBlock).where(ContentBlock.subject_id == subject_id)
                 .order_by(ContentBlock.id).offset(skip).limit(limit))
    return list(db.scalars(statement).all())


def create_block(db: Session, subject_id: int, payload: ContentBlockCreate) -> ContentBlock:
    get_subject(db, subject_id)
    block = ContentBlock(subject_id=subject_id, **payload.model_dump())
    db.add(block)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(block)
    return block


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
