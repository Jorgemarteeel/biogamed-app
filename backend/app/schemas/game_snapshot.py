"""Private storage contract; player responses must use QuestionForGame instead."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.game import QuestionForGame
from app.schemas.question import QuestionType


class StoredQuestion(QuestionForGame):
    model_config = ConfigDict(from_attributes=True, extra="forbid", strict=True)

    topic_id: int
    question_type: QuestionType
    options: list[str] | None
    letter: str | None
    correct_option_index: int | None
    exact_word: str | None
    accepted_answers: list[str] | None


class QuestionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1]
    questions: list[StoredQuestion] = Field(min_length=1, max_length=10)


class SharedQuestionSnapshot(BaseModel):
    """Private local-match history contract; legacy and Trivial limits stay unchanged."""
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[2]
    questions: list[StoredQuestion] = Field(min_length=20, max_length=20)
