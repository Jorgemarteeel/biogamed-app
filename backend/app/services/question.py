from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, Topic
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


def create_question(db: Session, question: QuestionCreate) -> Question:
    topic = db.execute(select(Topic).where(Topic.id == question.topic_id)).scalar_one_or_none()
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La temática no existe.",
        )

    db_question = Question(
        **question.model_dump(),
        correct_answer=(question.options[question.correct_option_index]
                        if question.question_type == "TRIVIAL"
                        else question.exact_word.strip()),
    )
    db.add(db_question)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(db_question)
    return db_question


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
) -> list[Question]:
    get_category(db, subject_id, block_id, category_id)
    if difficulty is not None and difficulty_unknown:
        raise HTTPException(422, "No se puede indicar difficulty junto con difficulty_unknown.")
    statement = select(Question).where(Question.category_id == category_id)
    if mode is not None:
        statement = statement.where(Question.question_type == mode)
    if difficulty is not None:
        statement = statement.where(Question.difficulty == difficulty)
    elif difficulty_unknown:
        statement = statement.where(Question.difficulty.is_(None))
    return list(db.scalars(statement.options(selectinload(Question.topic))
                           .order_by(Question.id).offset(skip).limit(limit)).all())
