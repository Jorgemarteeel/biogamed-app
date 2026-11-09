"""Public academic metadata; contains neither questions nor solutions."""
from pydantic import BaseModel


class AcademicContext(BaseModel):
    subject_id: int
    subject_name: str
    block_id: int
    block_name: str
    category_id: int
    category_name: str
