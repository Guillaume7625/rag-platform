from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None = None
    tenant_id: UUID
    role: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Fields a user can update on their own profile via PATCH /auth/me.

    Intentionally narrow for Phase 3A: only full_name. Password change,
    email change, and role management are explicitly out of scope.
    """

    full_name: str = Field(min_length=1, max_length=255)
