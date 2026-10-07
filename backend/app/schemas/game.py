from pydantic import BaseModel, ConfigDict, Field


class QuestionForGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    options: list[str]


class GameSessionStartResponse(BaseModel):
    session_id: int
    topic_id: int
    questions: list[QuestionForGame]


class UserAnswer(BaseModel):
    question_id: int = Field(gt=0, strict=True)
    selected_index: int = Field(ge=0, strict=True)


class GameSubmit(BaseModel):
    answers: list[UserAnswer] = Field(min_length=1, max_length=10)


class AnswerCorrection(BaseModel):
    question_id: int
    selected_index: int
    correct_option_index: int
    is_correct: bool


class GameResultResponse(BaseModel):
    score: int
    total_questions: int
    corrections: list[AnswerCorrection]
