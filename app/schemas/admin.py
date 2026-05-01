from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.admin import AnnouncementPriority, BuildingType, UnitStatus
from app.models.resident import ForumPostCategory


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


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=5, max_length=5000)
    priority: AnnouncementPriority = AnnouncementPriority.MEDIUM
    author_user_id: UUID | None = None
    published_at: datetime | None = None


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=5, max_length=5000)
    priority: AnnouncementPriority | None = None
    author_user_id: UUID | None = None
    published_at: datetime | None = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    priority: AnnouncementPriority
    author_user_id: UUID | None
    published_at: datetime
    created_at: datetime
    updated_at: datetime


class EventCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    event_date: datetime
    created_by: UUID
    is_active: bool = True


class EventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    event_date: datetime | None = None
    created_by: UUID | None = None
    is_active: bool | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    location: str | None
    event_date: datetime
    created_by: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ForumPostCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=5, max_length=5000)
    category: ForumPostCategory
    author_id: UUID
    is_pinned: bool = False


class ForumPostUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=5, max_length=5000)
    category: ForumPostCategory | None = None
    author_id: UUID | None = None
    is_pinned: bool | None = None
    upvotes: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ForumPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    category: ForumPostCategory
    author_id: UUID
    is_pinned: bool
    upvotes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
