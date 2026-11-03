from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Category, ContentBlock, Subject
from app.schemas.category import CategoryCreate
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


def get_block(db: Session, subject_id: int, block_id: int) -> ContentBlock:
    get_subject(db, subject_id)
    block = db.get(ContentBlock, block_id)
    if block is None or block.subject_id != subject_id:
        raise HTTPException(404, "El bloque no existe en esta asignatura.")
    return block


def get_categories(db: Session, subject_id: int, block_id: int,
                   skip: int = 0, limit: int = 100) -> list[Category]:
    get_block(db, subject_id, block_id)
    statement = (select(Category).where(Category.block_id == block_id)
                 .order_by(Category.id).offset(skip).limit(limit))
    return list(db.scalars(statement).all())


def get_unassigned_categories(db: Session, skip: int = 0, limit: int = 100) -> list[Category]:
    statement = (select(Category).where(Category.block_id.is_(None))
                 .order_by(Category.id).offset(skip).limit(limit))
    return list(db.scalars(statement).all())


def link_category(db: Session, subject_id: int, block_id: int, category_id: int) -> Category:
    get_block(db, subject_id, block_id)
    result = db.execute(
        update(Category).where(Category.id == category_id, Category.block_id.is_(None))
        .values(block_id=block_id).returning(Category.id),
        execution_options={"synchronize_session": False},
    ).scalar_one_or_none()
    if result is not None:
        db.commit()
        return db.get(Category, category_id)
    db.rollback()
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "La categoría no existe.")
    if category.block_id != block_id:
        raise HTTPException(409, "La categoría ya pertenece a otro bloque.")
    return category


def create_category(db: Session, subject_id: int, block_id: int,
                    payload: CategoryCreate) -> Category:
    get_block(db, subject_id, block_id)
    category = Category(block_id=block_id, **payload.model_dump())
    db.add(category)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(category)
    return category


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
