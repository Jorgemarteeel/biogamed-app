"""Internal card intents; no client-selected cards or oral answer transcript."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PresentCommand(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    operation_id: UUID
    expected_version: int = Field(strict=True, ge=1)
    participant_slot: int = Field(strict=True, ge=1, le=6)
    turn_number: int = Field(strict=True, ge=1)
    request_operation_id: UUID


class EvaluateCommand(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    operation_id: UUID
    expected_version: int = Field(strict=True, ge=1)
    participant_slot: int = Field(strict=True, ge=1, le=6)
    reader_slot: int = Field(strict=True, ge=1, le=6)
    turn_number: int = Field(strict=True, ge=1)
    presentation_id: int = Field(strict=True, ge=1)
    correct: bool = Field(strict=True)


class ReaderQuery(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    presentation_id: int = Field(strict=True, ge=1)
    reader_slot: int = Field(strict=True, ge=1, le=6)
