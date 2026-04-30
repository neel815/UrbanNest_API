from pydantic import BaseModel, EmailStr, Field

from app.models.resident import BuildingType, UnitStatus


class AdminDashboardStatsResponse(BaseModel):
    total_residents: int
    total_security: int
    total_managed_users: int
    residents_joined_last_30_days: int
    security_joined_last_30_days: int
    building_id: str | None = None
    building_name: str | None = None


class AdminBuildingInfoResponse(BaseModel):
    building_id: str
    building_name: str
    building_type: BuildingType


class InviteManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    profile_image: str | None = None
    unit_id: str | None = None


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
    unit_id: str | None = None


class UpdateManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    profile_image: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UnitResponse(BaseModel):
    id: str
    building_id: str
    unit_number: str
    floor: int | None
    plot_number: str | None
    status: UnitStatus
    resident_name: str | None = None


class UnitCreateRequest(BaseModel):
    unit_number: str = Field(min_length=1, max_length=50)
    floor: int | None = Field(default=None, ge=-10, le=200)
    plot_number: str | None = Field(default=None, max_length=50)
    status: UnitStatus = UnitStatus.VACANT


class UnitUpdateRequest(BaseModel):
    unit_number: str | None = Field(default=None, min_length=1, max_length=50)
    floor: int | None = Field(default=None, ge=-10, le=200)
    plot_number: str | None = Field(default=None, max_length=50)
    status: UnitStatus | None = None