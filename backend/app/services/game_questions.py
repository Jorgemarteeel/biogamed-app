"""Shared availability filter for topic selection and game creation."""
from sqlalchemy import and_

from app.models import Question


def playable_question_filter(mode: str):
    fields = (
        (Question.options.is_not(None), Question.correct_option_index.is_not(None))
        if mode == "TRIVIAL"
        else (Question.letter.is_not(None), Question.exact_word.is_not(None))
    )
    return and_(Question.question_type == mode, *fields)
