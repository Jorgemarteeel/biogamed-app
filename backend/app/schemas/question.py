from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


# The legacy correct_answer column accepts at most 255 characters.
AnswerOption = Annotated[str, Field(min_length=1, max_length=255)]


class QuestionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str = Field(min_length=1)
    options: list[AnswerOption] = Field(min_length=4, max_length=4)
    correct_option_index: int = Field(ge=0, le=3)
    topic_id: int = Field(gt=0)


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str | None = Field(default=None, min_length=1)
    options: list[AnswerOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_option_index: int | None = Field(default=None, ge=0, le=3)
    topic_id: int | None = Field(default=None, gt=0)

    @field_validator("text", "options", "correct_option_index", "topic_id")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("El campo puede omitirse, pero no puede ser null.")
        return value


class QuestionResponse(QuestionBase):
    id: int
