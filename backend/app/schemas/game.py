from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.question import QuestionType


class QuestionForGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    options: list[str] | None = None
    question_type: QuestionType = "TRIVIAL"
    letter: str | None = None


class GameSessionStartResponse(BaseModel):
    session_id: int
    topic_id: int
    questions: list[QuestionForGame]


class UserAnswer(BaseModel):
    question_id: int = Field(gt=0, strict=True)
    selected_index: int | None = Field(default=None, ge=0, strict=True)
    text_answer: str | None = None
    response_time_ms: int | None = Field(default=None, ge=0, le=2147483647, strict=True)


class GameSubmit(BaseModel):
    answers: list[UserAnswer] = Field(min_length=1, max_length=10)


class AnswerCorrection(BaseModel):
    question_id: int
    selected_index: int | None = None
    correct_option_index: int | None = None
    text_answer: str | None = None
    exact_word: str | None = None
    is_correct: bool


class GameResultResponse(BaseModel):
    score: int
    total_questions: int
    corrections: list[AnswerCorrection]


class AnswerHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    question_text: str
    question_type: QuestionType
    options: list[str] | None
    letter: str | None
    selected_index: int | None
    text_answer: str | None
    correct_option_index: int | None
    exact_word: str | None
    is_correct: bool
    response_time_ms: int | None
    answered_at: datetime


class GameHistorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    game_mode: QuestionType
    score: int
    is_completed: bool
    created_at: datetime
    question_ids: list[int]


class GameHistoryDetail(GameHistorySummary):
    answer_logs: list[AnswerHistory]
