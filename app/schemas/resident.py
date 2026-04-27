from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.resident import (
    AnnouncementPriority,
    BuildingStatus,
    ForumPostCategory,
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceStatus,
    PaymentStatus,
    PaymentType,
    SecurityShift,
    UnitStatus,
    VisitorStatus,
)


class BuildingCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: str = Field(min_length=5, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: BuildingStatus = BuildingStatus.ACTIVE


class BuildingUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    address: str | None = Field(default=None, min_length=5, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: BuildingStatus | None = None


class BuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    description: str | None
    status: BuildingStatus
    created_at: datetime
    updated_at: datetime


class UnitCreateRequest(BaseModel):
    building_id: UUID
    unit_number: str = Field(min_length=1, max_length=50)
    floor_number: int | None = Field(default=None, ge=-10, le=200)
    size_sqft: int | None = Field(default=None, ge=0)
    status: UnitStatus = UnitStatus.AVAILABLE


class UnitUpdateRequest(BaseModel):
    building_id: UUID | None = None
    unit_number: str | None = Field(default=None, min_length=1, max_length=50)
    floor_number: int | None = Field(default=None, ge=-10, le=200)
    size_sqft: int | None = Field(default=None, ge=0)
    status: UnitStatus | None = None


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID
    unit_number: str
    floor_number: int | None
    size_sqft: int | None
    status: UnitStatus
    created_at: datetime
    updated_at: datetime


class ResidentProfileCreateRequest(BaseModel):
    user_id: UUID
    unit_id: UUID | None = None
    move_in_date: datetime | None = None
    move_out_date: datetime | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class ResidentProfileUpdateRequest(BaseModel):
    unit_id: UUID | None = None
    move_in_date: datetime | None = None
    move_out_date: datetime | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class ResidentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    unit_id: UUID | None
    move_in_date: datetime | None
    move_out_date: datetime | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime


class SecurityProfileCreateRequest(BaseModel):
    user_id: UUID
    badge_number: str | None = Field(default=None, max_length=64)
    shift: SecurityShift = SecurityShift.ROTATING
    assigned_building_id: UUID | None = None
    is_active: bool = True


class SecurityProfileUpdateRequest(BaseModel):
    badge_number: str | None = Field(default=None, max_length=64)
    shift: SecurityShift | None = None
    assigned_building_id: UUID | None = None
    is_active: bool | None = None


class SecurityProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    badge_number: str | None
    shift: SecurityShift
    assigned_building_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


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


class MaintenanceRequestCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=5, max_length=5000)
    category: MaintenanceCategory
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    unit_id: UUID | None = None
    photo_url: str | None = Field(default=None, max_length=5000)


class MaintenanceRequestUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, min_length=5, max_length=5000)
    category: MaintenanceCategory | None = None
    priority: MaintenancePriority | None = None
    status: MaintenanceStatus | None = None
    unit_id: UUID | None = None
    photo_url: str | None = Field(default=None, max_length=5000)
    resolved_at: datetime | None = None


class MaintenanceRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    category: MaintenanceCategory
    priority: MaintenancePriority
    status: MaintenanceStatus
    resident_id: UUID
    unit_id: UUID | None
    photo_url: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VisitorCreateRequest(BaseModel):
    visitor_name: str = Field(min_length=2, max_length=150)
    visitor_phone: str | None = Field(default=None, max_length=30)
    purpose: str | None = Field(default=None, max_length=5000)
    expected_date: date
    approved_by: UUID | None = None


class VisitorUpdateRequest(BaseModel):
    visitor_name: str | None = Field(default=None, min_length=2, max_length=150)
    visitor_phone: str | None = Field(default=None, max_length=30)
    purpose: str | None = Field(default=None, max_length=5000)
    expected_date: date | None = None
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    status: VisitorStatus | None = None
    approved_by: UUID | None = None


class VisitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_name: str
    visitor_phone: str | None
    purpose: str | None
    resident_id: UUID
    expected_date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: VisitorStatus
    approved_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PaymentCreateRequest(BaseModel):
    amount: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
    type: PaymentType
    status: PaymentStatus = PaymentStatus.PENDING
    due_date: date
    paid_date: date | None = None
    transaction_ref: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=5000)


class PaymentUpdateRequest(BaseModel):
    amount: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)] | None = None
    type: PaymentType | None = None
    status: PaymentStatus | None = None
    due_date: date | None = None
    paid_date: date | None = None
    transaction_ref: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=5000)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resident_id: UUID
    amount: Decimal
    type: PaymentType
    status: PaymentStatus
    due_date: date
    paid_date: date | None
    transaction_ref: str | None
    description: str | None
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
