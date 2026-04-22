from pydantic import BaseModel, EmailStr, Field


class DashboardStatsResponse(BaseModel):
    total_users: int
    total_admins: int
    total_residents: int
    total_security: int
    residents_joined_last_30_days: int


class UserSummary(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    created_at: str
    must_reset_password: bool
    profile_image_url: str | None = None


class AdminInviteRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr


class AdminInviteResponse(BaseModel):
    message: str
    reset_link: str


class SettingsUpdateRequest(BaseModel):
    app_name: str = Field(min_length=2, max_length=100)
    full_name: str = Field(min_length=2, max_length=100)
    profile_image_url: str | None = None
