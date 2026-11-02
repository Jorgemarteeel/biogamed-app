from pydantic import BaseModel, ConfigDict

from app.schemas.subject import SubjectCreate


class ContentBlockCreate(SubjectCreate):
    """A block has the same editable fields as a subject."""


class ContentBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    name: str
    description: str | None
