from pydantic import BaseModel, EmailStr, Field


class AdminDashboardStatsResponse(BaseModel):
    total_residents: int
    total_security: int
    total_managed_users: int
    residents_joined_last_30_days: int
    security_joined_last_30_days: int


class InviteManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    profile_image: str | None = None


class InviteManagedUserResponse(BaseModel):
    message: str
    reset_link: str


class ManagedUserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    profile_image: str | None = None
    created_at: str


class CreateManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    profile_image: str | None = None


class UpdateManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    profile_image: str | None = None
    password: str | None = Field(default=None, min_length=8)