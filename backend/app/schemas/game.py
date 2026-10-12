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
