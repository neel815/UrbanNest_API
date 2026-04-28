from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole


class MeResponse(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr
    role: UserRole
    profile_image: str | None = None


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    profile_image: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)
