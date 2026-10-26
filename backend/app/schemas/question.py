from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.utils.answers import normalize_answer


# The legacy correct_answer column accepts at most 255 characters.
AnswerOption = Annotated[str, Field(min_length=1, max_length=255)]
QuestionType = Literal["TRIVIAL", "PASAPALABRA"]


class AcceptedAnswers(BaseModel):
    accepted_answers: list[AnswerOption] = Field(default_factory=list, max_length=30)

    @field_validator("accepted_answers")
    @classmethod
    def clean_answers(cls, values):
        result = []
        seen = set()
        for value in values:
            normalized = normalize_answer(value)
            if not normalized:
                raise ValueError("Las respuestas alternativas no pueden estar vacías.")
            if normalized not in seen:
                result.append(" ".join(value.split()))
                seen.add(normalized)
        return result


class QuestionSynonymsUpdate(AcceptedAnswers):
    accepted_answers: list[AnswerOption] = Field(max_length=30)


class QuestionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str = Field(min_length=1)
    options: list[AnswerOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_option_index: int | None = Field(default=None, ge=0, le=3)
    topic_id: int = Field(gt=0)
    question_type: QuestionType = "TRIVIAL"
    letter: str | None = Field(default=None, min_length=1, max_length=1)
    exact_word: str | None = Field(default=None, min_length=1, max_length=255)
    accepted_answers: list[AnswerOption] | None = Field(default=None, max_length=30)


class QuestionCreate(QuestionBase):
    @field_validator("accepted_answers")
    @classmethod
    def clean_answers(cls, value):
        return AcceptedAnswers(accepted_answers=value).accepted_answers if value is not None else None

    @model_validator(mode="after")
    def validate_game_fields(self):
        if self.question_type == "TRIVIAL":
            if self.accepted_answers:
                raise ValueError("Las respuestas alternativas solo se utilizan en PASAPALABRA.")
            if self.options is None or self.correct_option_index is None:
                raise ValueError("TRIVIAL requiere options y correct_option_index.")
        else:
            if self.letter is None or not self.letter.isalpha():
                raise ValueError("PASAPALABRA requiere una letra alfabética.")
            if self.exact_word is None or not self.exact_word.strip():
                raise ValueError("PASAPALABRA requiere exact_word.")
            word = normalize_answer(self.exact_word)
            letter = normalize_answer(self.letter)
            contains = self.text.strip().casefold().startswith("contiene la letra ")
            if contains:
                if letter not in word:
                    raise ValueError("exact_word debe contener letter.")
            elif not word.startswith(letter):
                raise ValueError("exact_word debe empezar por letter.")
        return self


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str | None = Field(default=None, min_length=1)
    options: list[AnswerOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_option_index: int | None = Field(default=None, ge=0, le=3)
    topic_id: int | None = Field(default=None, gt=0)
    question_type: QuestionType | None = None
    letter: str | None = Field(default=None, min_length=1, max_length=1)
    exact_word: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("text", "topic_id", "question_type")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("El campo puede omitirse, pero no puede ser null.")
        return value


class QuestionResponse(QuestionBase):
    id: int
