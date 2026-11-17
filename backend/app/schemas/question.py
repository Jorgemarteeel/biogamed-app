from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, model_serializer
from app.utils.answers import normalize_answer
from app.schemas.topic import TopicResponse


# The legacy correct_answer column accepts at most 255 characters.
AnswerOption = Annotated[str, Field(min_length=1, max_length=255)]
QuestionType = Literal["TRIVIAL", "PASAPALABRA"]
ContentType = Literal["TRIVIAL", "PASAPALABRA", "INMUNOQUEST"]
Bank = Literal["LYMPHOCYTE", "MACROPHAGE", "SPLEEN", "FLASK", "DNA"]
Difficulty = Annotated[int, Field(
    strict=True, ge=1, le=4,
    description="Nivel de origen del prototipo (1–4); significado académico pendiente de validación.",
)]


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
    difficulty: Difficulty | None = None
    options: list[AnswerOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_option_index: int | None = Field(default=None, ge=0, le=3)
    topic_id: int | None = Field(default=None, gt=0)
    question_type: ContentType = "TRIVIAL"
    letter: str | None = Field(default=None, min_length=1, max_length=1)
    exact_word: str | None = Field(default=None, min_length=1, max_length=255)
    accepted_answers: list[AnswerOption] | None = Field(default=None, max_length=30)


    reference_answer: str | None = Field(default=None, min_length=1, max_length=10000)
    bank: Bank | None = None
    note_reference: str | None = Field(default=None, max_length=120)

    @model_serializer(mode="wrap")
    def legacy_shape(self, handler):
        result = handler(self)
        if self.question_type != "INMUNOQUEST":
            for key in ("reference_answer", "bank", "note_reference"):
                result.pop(key, None)
        return result


class QuestionCreate(QuestionBase):
    subject_id: int | None = Field(default=None, gt=0)
    block_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)

    @field_validator("text", "options")
    @classmethod
    def reject_blank_content(cls, value):
        values = value if isinstance(value, list) else [value]
        if any(isinstance(item, str) and not item.strip() for item in values):
            raise ValueError("El enunciado y las opciones no pueden estar vacíos.")
        return value

    @field_validator("accepted_answers")
    @classmethod
    def clean_answers(cls, value):
        return AcceptedAnswers(accepted_answers=value).accepted_answers if value is not None else None

    @model_validator(mode="after")
    def validate_game_fields(self):
        if self.question_type == "INMUNOQUEST":
            if self.topic_id is not None:
                raise ValueError("InmunoQuest no utiliza una temática Topic.")
            if self.bank is None or self.difficulty is None or not self.reference_answer or not self.reference_answer.strip():
                raise ValueError("InmunoQuest requiere banco, dificultad 1–4 y respuesta de referencia.")
            if any(v is not None for v in (self.options, self.correct_option_index, self.letter, self.exact_word, self.accepted_answers)):
                raise ValueError("La pregunta abierta no admite opciones, letra ni alternativas.")
            self.text = self.text.strip()
            self.reference_answer = self.reference_answer.strip()
            self.note_reference = self.note_reference.strip() or None if self.note_reference else None
            return self
        if self.topic_id is None:
            raise ValueError("La temática es obligatoria para este formato.")
        if any(v is not None for v in (self.bank, self.reference_answer, self.note_reference)):
            raise ValueError("Los campos de pregunta abierta no pertenecen a este formato.")
        if self.question_type == "TRIVIAL":
            if self.letter is not None or self.exact_word is not None:
                raise ValueError("TRIVIAL no admite letter ni exact_word.")
            if self.accepted_answers:
                raise ValueError("Las respuestas alternativas solo se utilizan en PASAPALABRA.")
            if self.options is None or self.correct_option_index is None:
                raise ValueError("TRIVIAL requiere options y correct_option_index.")
        else:
            if self.options is not None or self.correct_option_index is not None:
                raise ValueError("PASAPALABRA no admite opciones de TRIVIAL.")
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


class CategoryQuestionCreate(QuestionCreate):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def route_owns_destination(cls, value):
        if isinstance(value, dict) and any(key in value for key in ("subject_id", "block_id", "category_id")):
            raise ValueError("El destino de esta operación se indica en la ruta, no en el contenido.")
        return value


class CategoryQuestionEdit(CategoryQuestionCreate):
    question_type: ContentType


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str | None = Field(default=None, min_length=1)
    difficulty: Difficulty | None = None
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


class QuestionStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool = Field(strict=True)


class QuestionResponse(QuestionBase):
    id: int
    is_active: bool


class CategoryQuestionResponse(QuestionResponse):
    category_id: int
    topic: TopicResponse | None | None
