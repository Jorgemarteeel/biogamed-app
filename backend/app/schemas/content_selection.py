"""Public academic metadata; contains neither questions nor solutions."""
from pydantic import BaseModel


class AcademicContext(BaseModel):
    subject_id: int
    subject_name: str
    block_id: int | None = None
    block_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    edition_id: int | None = None
    academic_year: str | None = None
    topic_id: int | None = None
    topic_name: str | None = None
    difficulty: int | None = None
