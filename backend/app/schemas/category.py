from pydantic import BaseModel, ConfigDict

from app.schemas.subject import SubjectCreate, SubjectResponse


class CategoryCreate(SubjectCreate):
    """The name and description follow the existing academic content rules."""


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    block_id: int
    name: str
    description: str | None


class BlockDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    name: str
    description: str | None
    subject: SubjectResponse
