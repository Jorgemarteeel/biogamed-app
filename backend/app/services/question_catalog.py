"""Staff question catalog and explicit academic destinations; never game selection."""
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models import Question, Subject, ContentBlock, Category
from app.schemas.question import QuestionResponse


def academic_destination(db, subject_id=None, block_id=None, category_id=None):
    category = db.get(Category, category_id) if category_id else None
    if category_id and category is None:
        raise HTTPException(404, "La categoría no existe.")
    if category and category.block_id:
        if block_id and block_id != category.block_id:
            raise HTTPException(422, "El bloque no corresponde a la categoría.")
        block_id = category.block_id
    elif category and block_id:
        raise HTTPException(422, "La categoría no pertenece al bloque seleccionado.")
    block = db.get(ContentBlock, block_id) if block_id else None
    if block_id and block is None:
        raise HTTPException(404, "El bloque no existe.")
    if block:
        if subject_id and subject_id != block.subject_id:
            raise HTTPException(422, "La asignatura no corresponde al bloque o categoría.")
        subject_id = block.subject_id
    if subject_id and db.get(Subject, subject_id) is None:
        raise HTTPException(404, "La asignatura no existe.")
    return dict(subject_id=subject_id, block_id=block_id, category_id=category_id)


def public_staff_row(q):
    return {**QuestionResponse.model_validate(q).model_dump(),
            "subject_id": q.subject_id, "subject_name": q.subject.name if q.subject else None,
            "block_id": q.block_id, "block_name": q.block.name if q.block else None,
            "category_id": q.category_id, "category_name": q.category.name if q.category else None,
            "topic_name": q.topic.name if q.topic else None, "topic": {"id": q.topic.id, "name": q.topic.name, "description": q.topic.description} if q.topic else None}


def catalog(db, *, mode=None, subject_id=None, block_id=None, category_id=None,
            difficulty=None, difficulty_unknown=False, state="all", bank=None,
            classification="all", skip=0, limit=20):
    resolved = academic_destination(db, subject_id, block_id, category_id)
    if difficulty_unknown and difficulty is not None:
        raise HTTPException(422, "Selecciona dificultad o sin dificultad, no ambas.")
    if bank and mode != "INMUNOQUEST":
        raise HTTPException(422, "El filtro de banco requiere InmunoQuest.")
    if classification == "unassigned" and any(resolved.values()):
        raise HTTPException(422, "Sin asignatura es incompatible con filtros académicos.")
    stmt = select(Question)
    if mode: stmt = stmt.where(Question.question_type == mode)
    if state != "all": stmt = stmt.where(Question.is_active.is_(state == "active"))
    if classification == "unassigned": stmt = stmt.where(Question.subject_id.is_(None))
    elif classification == "uncategorized": stmt = stmt.where(Question.category_id.is_(None))
    for field, value in resolved.items():
        if value is not None: stmt = stmt.where(getattr(Question, field) == value)
    if difficulty is not None: stmt = stmt.where(Question.difficulty == difficulty)
    elif difficulty_unknown: stmt = stmt.where(Question.difficulty.is_(None))
    if bank: stmt = stmt.where(Question.bank == bank)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.options(selectinload(Question.subject), selectinload(Question.block), selectinload(Question.category), selectinload(Question.topic)).order_by(Question.id).offset(skip).limit(limit))
    return {"items": [public_staff_row(q) for q in rows], "total": total, "skip": skip, "limit": limit}
