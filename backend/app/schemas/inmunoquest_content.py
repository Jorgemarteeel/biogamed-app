"""Private open-question snapshot v2. Never use as a player response schema."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoredOpenQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: int = Field(strict=True, gt=0)
    question_type: Literal['INMUNOQUEST']
    text: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1, max_length=10000)
    note_reference: str | None = Field(default=None, max_length=120)

    @field_validator('text', 'reference_answer')
    @classmethod
    def nonblank_without_rewriting(cls, value):
        if not value.strip():
            raise ValueError('Private question content must be nonblank')
        return value
