from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Question, Topic
from app.schemas.question import QuestionCreate


def create_question(db: Session, question: QuestionCreate) -> Question:
    topic = db.execute(select(Topic).where(Topic.id == question.topic_id)).scalar_one_or_none()
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La temática no existe.",
        )

    db_question = Question(
        **question.model_dump(),
        correct_answer=question.options[question.correct_option_index],
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
            Question.options.is_not(None),
            Question.correct_option_index.is_not(None),
        )
        .order_by(Question.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())
