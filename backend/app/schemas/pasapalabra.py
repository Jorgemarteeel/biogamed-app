from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.content_selection import AcademicContext


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: int | None = Field(default=None, gt=0, strict=True)
    subject_id: int | None = Field(default=None, gt=0, strict=True)
    block_id: int | None = Field(default=None, gt=0, strict=True)
    category_id: int | None = Field(default=None, gt=0, strict=True)
    difficulty: int | None = Field(default=None, ge=1, le=4, strict=True)
    difficulty_unknown: bool = False

    @model_validator(mode="after")
    def exclusive_difficulty(self):
        if self.difficulty is not None and self.difficulty_unknown:
            raise ValueError("difficulty y difficulty_unknown son excluyentes")
        academic = self.subject_id is not None or self.block_id is not None
        if academic and (self.subject_id is None or self.block_id is None or self.category_id is None or self.topic_id is not None):
            raise ValueError("La selección académica requiere asignatura, bloque y categoría sin temática")
        if not academic and self.topic_id is None:
            raise ValueError("Falta la selección de contenido")
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
    academic: AcademicContext | None = None
    id: int
    version: int
    play_mode: Literal["LOCAL", "ONLINE"]
    self_position: int = 1
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


class RoomCreate(Selection):
    operation_id: UUID


class RoomJoin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    code: str = Field(min_length=1, max_length=12)


class RoomAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    expected_version: int = Field(ge=1, strict=True)


class RoomConfiguration(BaseModel):
    academic: AcademicContext | None = None
    topic: str | None
    category: str
    difficulty: int | None
    difficulty_unknown: bool
    questions_per_player: Literal[20]
    time_per_player_ms: Literal[600000]


class RoomParticipant(BaseModel):
    position: int
    name: str
    ready: bool


class RoomState(BaseModel):
    id: int
    version: int
    status: Literal["WAITING", "STARTED", "CANCELLED", "EXPIRED"]
    self_position: int
    configuration: RoomConfiguration
    selection: Selection
    code: str | None
    expires_at: datetime
    server_now: datetime
    match_id: int | None
    participants: list[RoomParticipant]


class RoomLeft(BaseModel):
    id: int
    status: Literal["LEFT"]
