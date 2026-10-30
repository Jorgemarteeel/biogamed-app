"""Shared availability filter for topic selection and game creation."""
from fastapi import HTTPException
from sqlalchemy import and_, select

from app.models import Question


def playable_question_filter(mode: str):
    fields = (
        (Question.options.is_not(None), Question.correct_option_index.is_not(None))
        if mode == "TRIVIAL"
        else (Question.letter.is_not(None), Question.exact_word.is_not(None))
    )
    return and_(Question.question_type == mode, *fields)


def selectable_questions(topic_id: int, mode: str, category_id: int | None = None,
                         difficulty: int | None = None, difficulty_unknown: bool = False):
    if mode not in {"TRIVIAL", "PASAPALABRA"}:
        raise HTTPException(422, "El modo debe ser TRIVIAL o PASAPALABRA.")
    if category_id is not None and (type(category_id) is not int or category_id < 1):
        raise HTTPException(422, "category_id debe ser un entero positivo.")
    if difficulty is not None and (type(difficulty) is not int or difficulty not in range(1, 5)):
        raise HTTPException(422, "difficulty debe ser un entero entre 1 y 4.")
    if difficulty_unknown and difficulty is not None:
        raise HTTPException(422, "No se puede indicar difficulty junto con difficulty_unknown.")
    statement = select(Question).where(
        Question.topic_id == topic_id, playable_question_filter(mode),
    )
    if category_id is not None:
        statement = statement.where(Question.category_id == category_id)
    if difficulty is not None:
        statement = statement.where(Question.difficulty == difficulty)
    elif difficulty_unknown:
        statement = statement.where(Question.difficulty.is_(None))
    return statement
