from pydantic import BaseModel, ConfigDict, Field


class TopicBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class TopicCreate(TopicBase):
    pass


class TopicResponse(TopicBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
