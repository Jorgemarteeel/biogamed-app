from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: int = Field(gt=0, strict=True)
    category_id: int | None = Field(default=None, gt=0, strict=True)
    difficulty: int | None = Field(default=None, ge=1, le=4, strict=True)
    difficulty_unknown: bool = False

    @model_validator(mode="after")
    def exclusive_difficulty(self):
        if self.difficulty is not None and self.difficulty_unknown:
            raise ValueError("difficulty y difficulty_unknown son excluyentes")
        return self


class LocalStart(Selection):
    operation_id: UUID
    guest_name: str = Field(min_length=1, max_length=255)

    @field_validator("guest_name")
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError("El invitado necesita un nombre")
        return value.strip()


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    expected_version: int = Field(ge=1, strict=True)
    participant: int = Field(ge=1, le=2, strict=True)
    number: int = Field(ge=1, le=20, strict=True)


class Answer(Command):
    text_answer: str = Field(min_length=1, max_length=2000)

    @field_validator("text_answer")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("La respuesta no puede estar vacía")
        return value


class Abandon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    expected_version: int = Field(ge=1, strict=True)
    participant: int = Field(ge=1, le=2, strict=True)


class PublicSlot(BaseModel):
    number: int
    state: Literal["PENDING", "PASSED", "CORRECT", "WRONG"]


class ResolvedQuestion(BaseModel):
    number: int
    resolution_order: int
    text: str
    text_answer: str
    exact_word: str
    accepted_answers: list[str]
    is_correct: bool


class PublicParticipant(BaseModel):
    position: int
    name: str
    registered: bool
    status: str
    finish_reason: str | None
    remaining_ms: int
    correct: int
    wrong: int
    pending: int
    slots: list[PublicSlot]
    resolved: list[ResolvedQuestion]


class ActiveQuestion(BaseModel):
    participant: int
    number: int
    text: str
    letter: str


class MatchState(BaseModel):
    id: int
    version: int
    play_mode: Literal["LOCAL"]
    rules_version: str
    status: str
    server_now: datetime
    turn_deadline_at: datetime | None
    active_participant: int | None
    active_question: ActiveQuestion | None
    participants: list[PublicParticipant]
    outcome: str | None
    winner_position: int | None
    finished_at: datetime | None
    personal_session_id: int


class CommandResponse(BaseModel):
    operation: dict
    state: MatchState
