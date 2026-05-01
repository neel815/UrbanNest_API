from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.admin import BuildingStatus, BuildingType


class DashboardStatsResponse(BaseModel):
    total_users: int
    total_admins: int
    total_residents: int
    total_security: int
    residents_joined_last_30_days: int


class PlatformActivityItem(BaseModel):
    initials: str
    title: str
    timestamp: str
    level: str


class TopSocietyItem(BaseModel):
    name: str
    units: int
    occupancy_percent: int


class UserSummary(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    created_at: str
    must_reset_password: bool
    building_id: str | None = None
    building_name: str | None = None
    profile_image: str | None = None


class BuildingCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: str = Field(min_length=5, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    building_type: BuildingType = BuildingType.APARTMENT_TOWER
    status: BuildingStatus | None = None


class BuildingUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    address: str | None = Field(default=None, min_length=5, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    building_type: BuildingType | None = None
    status: BuildingStatus | None = None


class BuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    description: str | None
    building_type: BuildingType
    status: BuildingStatus
    created_at: datetime
    updated_at: datetime


class AdminInviteRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    building_id: UUID


class AdminInviteResponse(BaseModel):
    message: str
    reset_link: str


class SettingsUpdateRequest(BaseModel):
    app_name: str = Field(min_length=2, max_length=100)
    full_name: str = Field(min_length=2, max_length=100)
    profile_image: str | None = None
