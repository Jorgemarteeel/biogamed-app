from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Question, Topic
from app.services.subject import get_category
from app.schemas.question import QuestionCreate


def update_accepted_answers(db: Session, question_id: int, answers: list[str]) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(404, "La pregunta no existe.")
    if question.question_type != "PASAPALABRA":
        raise HTTPException(422, "Las respuestas alternativas solo se utilizan en PASAPALABRA.")
    question.accepted_answers = answers
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(question)
    return question


def _require_topic(db: Session, topic_id: int) -> None:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La temática no existe.",
        )


def _question_values(question: QuestionCreate) -> dict:
    values=question.model_dump()
    for key in ("subject_id", "block_id", "category_id"): values.pop(key, None)
    values["correct_answer"] = (None if question.question_type=="INMUNOQUEST" else question.options[question.correct_option_index] if question.question_type=="TRIVIAL" else question.exact_word.strip())
    return values


def lock_question_destination(db: Session, category_id: int | None) -> None:
    if category_id is not None:
        db.scalar(select(Category).where(Category.id==category_id).with_for_update().execution_options(populate_existing=True))
    elif db.bind.dialect.name=="postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(873460, 1)"))


def build_question(question: QuestionCreate, category_id: int | None = None, *, academic=None) -> Question:
    return Question(**_question_values(question), **(academic or {"category_id": category_id}))


def create_question(db: Session, question: QuestionCreate, *, category_id: int | None = None) -> Question:
    if question.question_type != "INMUNOQUEST": _require_topic(db, question.topic_id)
    from app.services.question_catalog import academic_destination
    if category_id and question.category_id and category_id != question.category_id:
        raise HTTPException(422, "La categoría del formulario contradice el destino.")
    academic = academic_destination(db, question.subject_id, question.block_id, category_id or question.category_id)
    lock_question_destination(db, academic["category_id"])
    academic = academic_destination(db, question.subject_id, question.block_id, category_id or question.category_id)
    db_question = build_question(question, academic=academic)
    db.add(db_question)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(db_question)
    return db_question


def create_category_question(db: Session, subject_id: int, block_id: int,
                             category_id: int, question: QuestionCreate) -> Question:
    get_category(db, subject_id, block_id, category_id)
    return create_question(db, question, category_id=category_id)


def edit_category_question(db: Session, subject_id: int, block_id: int, category_id: int,
                           question_id: int, payload: QuestionCreate) -> Question:
    get_category(db, subject_id, block_id, category_id)
    lock_question_destination(db, category_id)
    question = db.scalar(select(Question).where(
        Question.id == question_id, Question.category_id == category_id,
    ).with_for_update())
    if question is None:
        raise HTTPException(404, "La pregunta no existe en esta categoría.")
    if payload.question_type != question.question_type:
        raise HTTPException(422, "No se puede cambiar la modalidad de la pregunta.")
    if payload.question_type != "INMUNOQUEST": _require_topic(db, payload.topic_id)
    from app.services.question_catalog import academic_destination
    for field, value in (("subject_id", subject_id), ("block_id", block_id), ("category_id", category_id)):
        if getattr(payload, field) not in (None, value): raise HTTPException(422, "El destino del formulario contradice la ruta.")
    academic = academic_destination(db, subject_id, block_id, category_id)
    for field, value in academic.items(): setattr(question, field, value)
    for field, value in _question_values(payload).items():
        setattr(question, field, value)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(question)
    return question


def get_questions_by_topic(
    db: Session, topic_id: int, skip: int = 0, limit: int = 100
) -> list[Question]:
    statement = (
        select(Question)
        .where(
            Question.topic_id == topic_id,
            # Legacy free-text questions have no multiple-choice options.
            ((Question.question_type == "TRIVIAL")
             & Question.options.is_not(None)
             & Question.correct_option_index.is_not(None))
            | ((Question.question_type == "PASAPALABRA")
               & Question.letter.is_not(None)
               & Question.exact_word.is_not(None)),
        )
        .order_by(Question.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())


def get_questions_by_category(
    db: Session, subject_id: int, block_id: int, category_id: int,
    skip: int = 0, limit: int = 100, mode: str | None = None,
    difficulty: int | None = None, difficulty_unknown: bool = False,
    state: str = "all",
) -> list[Question]:
    get_category(db, subject_id, block_id, category_id)
    if difficulty is not None and difficulty_unknown:
        raise HTTPException(422, "No se puede indicar difficulty junto con difficulty_unknown.")
    statement = select(Question).where(Question.category_id == category_id)
    if mode is None:
        statement = statement.where(Question.question_type.in_(["TRIVIAL","PASAPALABRA"]))
    if state != "all":
        statement = statement.where(Question.is_active.is_(state == "active"))
    if mode is not None:
        statement = statement.where(Question.question_type == mode)
    else:
        statement = statement.where(Question.question_type.in_(["TRIVIAL","PASAPALABRA"]))
    if difficulty is not None:
        statement = statement.where(Question.difficulty == difficulty)
    elif difficulty_unknown:
        statement = statement.where(Question.difficulty.is_(None))
    return list(db.scalars(statement.options(selectinload(Question.topic))
                           .order_by(Question.id).offset(skip).limit(limit)).all())


def set_category_question_state(db: Session, subject_id: int, block_id: int, category_id: int,
                                question_id: int, is_active: bool) -> Question:
    get_category(db, subject_id, block_id, category_id)
    question = db.scalar(select(Question).where(
        Question.id == question_id, Question.category_id == category_id,
    ).with_for_update())
    if question is None:
        raise HTTPException(404, "La pregunta no existe en esta categoría.")
    question.is_active = is_active
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(question)
    return question
