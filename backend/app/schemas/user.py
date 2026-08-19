from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=255)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
