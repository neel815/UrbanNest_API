from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    society_name: str | None = None


class Announcement(BaseModel):
    id: str
    title: str
    content: str
    date: str
    priority: str
    author: str


class MaintenanceRequest(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    date: str
    lastUpdated: str


class MaintenanceCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=5, max_length=1000)
    category: str = Field(min_length=2, max_length=80)
    priority: str = Field(pattern="^(low|medium|high)$")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value


class Visitor(BaseModel):
    id: int
    name: str
    purpose: str
    date: str
    timeIn: str
    timeOut: Optional[str]
    status: str
    contactNumber: str
    vehicleNumber: Optional[str]


class VisitorCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    purpose: str = Field(min_length=2, max_length=200)
    date: str
    timeIn: str
    contactNumber: str = Field(min_length=5, max_length=30)
    vehicleNumber: Optional[str] = None


class VisitorStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(checked_in|checked_out)$")


class Payment(BaseModel):
    id: int
    type: str
    description: str
    amount: float
    dueDate: str
    status: str
    paidDate: Optional[str]
    paymentMethod: Optional[str]


class Event(BaseModel):
    id: int
    title: str
    description: str
    date: str
    time: str
    location: str
    type: str
    attendees: int
    maxAttendees: Optional[int]
    isRegistered: bool


class ForumPost(BaseModel):
    id: int
    title: str
    content: str
    author: str
    date: str
    category: str
    replies: int
    lastActivity: str


class ForumPostCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=5, max_length=3000)
    category: str = Field(pattern="^(general|complaints|suggestions|marketplace)$")


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
