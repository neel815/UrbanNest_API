from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.admin import AnnouncementPriority, BuildingType, UnitStatus
from app.models.resident import ForumPostCategory, MaintenanceStatus
from app.schemas.resident import MaintenanceRequestResponse


class AdminDashboardStatsResponse(BaseModel):
    total_residents: int
    total_security: int
    total_managed_users: int
    residents_joined_last_30_days: int
    security_joined_last_30_days: int
    building_id: str | None = None
    building_name: str | None = None


class SecurityOverviewResponse(BaseModel):
    total_security: int
    on_duty_now: int
    active_shifts: int
    building_id: str | None = None
    building_name: str | None = None


class AdminBuildingInfoResponse(BaseModel):
    building_id: str
    building_name: str
    building_type: BuildingType


class InviteManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=30)
    profile_image: str | None = None
    unit_id: str | None = None


class InviteManagedUserResponse(BaseModel):
    message: str
    reset_link: str


class ManagedUserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    role: str
    profile_image: str | None = None
    created_at: str
    must_reset_password: bool | None = None
    is_active: bool | None = None


class CreateManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8)
    profile_image: str | None = None
    unit_id: str | None = None


class UpdateManagedUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=30)
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


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=5, max_length=5000)
    priority: AnnouncementPriority | None = None
    author_user_id: UUID | None = None
    published_at: datetime | None = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID | None
    title: str
    content: str
    priority: AnnouncementPriority
    author_user_id: UUID | None
    published_at: datetime
    created_at: datetime
    updated_at: datetime


class MaintenanceStatusUpdateRequest(BaseModel):
    status: MaintenanceStatus
    resolution_note: str | None = None


class MaintenanceResolveRequest(BaseModel):
    resolution_note: str = Field(min_length=1)


class EventCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    event_date: datetime


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
    building_id: UUID | None
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


class MarkPaymentPaidRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=255)


class RaiseBulkDueRequest(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    due_date: str
    description: str | None = Field(default=None, max_length=500)


class RaiseIndividualDueRequest(BaseModel):
    resident_id: str
    type: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    due_date: str
    description: str | None = Field(default=None, max_length=500)


class ResidentListResponse(BaseModel):
    id: str
    full_name: str
    unit_number: str | None = None


class AdminResidentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    full_name: str
    email: str
    profile_image: str | None = None
    unit_number: str | None = None
    floor: int | None = None
    plot_number: str | None = None
    building_name: str | None = None
    move_in_date: date | None = None
    lease_end_date: date | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    total_maintenance_requests: int
    open_maintenance_requests: int
    total_payments: int
    pending_payments: int
    total_visitors: int
