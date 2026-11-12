from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr


class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=8, max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        value.encode("utf-8")
        return value


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole


class OwnNameUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class OwnPasswordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)
    confirmation: str = Field(min_length=8, max_length=255)

    @field_validator("new_password", "confirmation")
    @classmethod
    def valid_password(cls, value):
        value.encode("utf-8")
        return value
