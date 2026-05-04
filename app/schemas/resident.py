from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.admin import AnnouncementPriority
from app.models.resident import (
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceStatus,
    PaymentStatus,
    PaymentType,
    VisitorStatus,
)


class DashboardStats(BaseModel):
    announcements_count: int
    pending_maintenance: int
    active_visitors: int
    total_due: float


class ResidentProfileSummary(BaseModel):
    full_name: str
    unit_number: str | None = None
    building_name: str | None = None


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


class MaintenanceCreateRequest(BaseModel):
    title: str
    description: str
    category: MaintenanceCategory
    priority: MaintenancePriority


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
    visitor_name: str
    visitor_phone: str | None = None
    purpose: str | None = None
    expected_date: date
    vehicle_number: str | None = None


class VisitorUpdateRequest(BaseModel):
    status: VisitorStatus | None = None
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None


class VisitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_name: str
    visitor_phone: str | None
    purpose: str | None
    vehicle_number: str | None = None
    resident_id: UUID
    expected_date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: VisitorStatus
    approved_by: UUID | None
    created_at: datetime
    updated_at: datetime


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
    title: str
    content: str
    category: str


class ForumPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    category: str
    author_id: UUID
    is_pinned: bool
    upvotes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResidentProfileUpdateRequest(BaseModel):
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class ResidentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    unit_id: UUID | None
    move_in_date: datetime | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime
