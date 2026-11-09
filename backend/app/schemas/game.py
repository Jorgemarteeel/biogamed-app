from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_serializer
from app.schemas.content_selection import AcademicContext
from app.schemas.question import QuestionType


class QuestionForGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    options: list[str] | None = None
    question_type: QuestionType = "TRIVIAL"
    letter: str | None = None


class QuestionClassification(BaseModel):
    @model_serializer(mode="wrap")
    def preserve_legacy_shape(self, handler):
        value = handler(self)
        if value.get("topic_id") is None:
            value.pop("topic_id", None)
        return value

    question_id: int
    topic_id: int | None = None
    category_id: int | None
    category_name: str | None
    difficulty: int | None
    block_id: int | None = None
    block_name: str | None = None
    subject_id: int | None = None
    subject_name: str | None = None


class SelectionContext(BaseModel):
    category_id: int | None
    category_name: str | None
    difficulty: int | None
    difficulty_unknown: bool


class ContentContext(BaseModel):
    @model_serializer(mode="wrap")
    def preserve_legacy_shape(self, handler):
        value = handler(self)
        if value.get("academic") is None:
            value.pop("academic", None)
        return value

    topic_name: str | None = None
    academic: AcademicContext | None = None
    selection: SelectionContext
    questions: list[QuestionClassification]


class AvailableCombination(BaseModel):
    category_id: int | None
    category_name: str | None
    difficulty: int | None
    count: int


class GameAvailabilityResponse(BaseModel):
    academic: AcademicContext | None = None
    topic_id: int | None
    game_mode: QuestionType
    total_questions: int
    combinations: list[AvailableCombination]


class GameSessionStartResponse(BaseModel):
    session_id: int
    topic_id: int | None
    questions: list[QuestionForGame]
    content_context: ContentContext | None = None


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
    accepted_answers: list[str] | None
    is_correct: bool
    response_time_ms: int | None
    answered_at: datetime


class GameHistorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int | None
    game_mode: QuestionType
    score: int
    is_completed: bool
    created_at: datetime
    question_ids: list[int]
    content_context: ContentContext | None = None
    shared_match_id: int | None = None
    format_key: str | None = None
    match_status: str | None = None
    completion_reason: str | None = None
    wrong_count: int | None = None
    pending_count: int | None = None


class SharedParticipantSummary(BaseModel):
    position: int
    name: str
    correct: int
    wrong: int
    pending: int


class SharedMatchSummary(BaseModel):
    id: int
    play_mode: Literal["LOCAL", "ONLINE"]
    self_position: int
    status: str
    outcome: str | None
    winner_position: int | None
    participants: list[SharedParticipantSummary]


class GameHistoryDetail(GameHistorySummary):
    shared_summary: SharedMatchSummary | None = None
    continuation_error_code: Literal["LEGACY_SESSION_NO_SNAPSHOT"] | None = None
    question_content_source: Literal["session_start", "legacy"] = "legacy"
    answer_logs: list[AnswerHistory]

    @field_validator("answer_logs")
    @classmethod
    def hide_unfinished_corrections(cls, value, info: ValidationInfo):
        return value if info.data.get("is_completed") or info.data.get("match_status") == "FINISHED" else []


class ActivityCounts(BaseModel):
    started: int
    completed: int
    unfinished: int


class ComparableResult(BaseModel):
    session_id: int
    started_at: datetime
    score: int
    total_questions: int


class PersonalBestMark(BaseModel):
    academic: AcademicContext | None = None
    game_mode: QuestionType
    format_key: str | None = None
    topic_id: int | None
    topic_name: str | None
    topic_name_source: str | None = None
    category_id: int
    category_name: str | None
    category_name_source: str | None
    difficulty: int
    total_questions: int
    best_score: int
    session_id: int
    started_at: datetime
    valid_results: int
    tied_best_results: int
    results: list[ComparableResult]


class GameProgressResponse(ActivityCounts):
    by_mode: dict[QuestionType, ActivityCounts]
    best_marks: list[PersonalBestMark]
