from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.security.auth import UserRole


def _validate_email(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or "@" not in value:
        raise ValueError("Email must be a non-empty string containing '@'")
    return value


class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email", "username")
    @classmethod
    def validate_identity(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_email(value)

    @property
    def resolved_email(self) -> str:
        return (self.email or self.username or "").strip()

    @property
    def has_identity(self) -> bool:
        return bool(self.resolved_email)


class UserCreateRequest(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=200)
    role: UserRole = "viewer"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value) or value


class UserRead(BaseModel):
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime | None = None


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
