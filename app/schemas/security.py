from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.security import SecurityShift
from app.schemas.resident import VisitorResponse


class SecurityProfileCreateRequest(BaseModel):
    user_id: UUID
    badge_number: str | None = Field(default=None, max_length=64)
    shift: SecurityShift = SecurityShift.ROTATING
    shift_start_time: str | None = Field(default=None, max_length=5)
    shift_end_time: str | None = Field(default=None, max_length=5)
    assigned_gate: str | None = Field(default=None, max_length=150)
    assigned_building_id: UUID | None = None
    is_active: bool = True


class SecurityProfileUpdateRequest(BaseModel):
    badge_number: str | None = Field(default=None, max_length=64)
    shift: SecurityShift | None = None
    shift_start_time: str | None = Field(default=None, max_length=5)
    shift_end_time: str | None = Field(default=None, max_length=5)
    assigned_gate: str | None = Field(default=None, max_length=150)
    assigned_building_id: UUID | None = None
    is_active: bool | None = None


class SecurityProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    badge_number: str | None
    shift: SecurityShift
    shift_start_time: str | None
    shift_end_time: str | None
    assigned_gate: str | None
    assigned_building_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DashboardStats(BaseModel):
    activeVisitors: int
    pendingApprovals: int
    incidentsToday: int
    patrolRounds: int
    accessAlerts: int
    totalEntries: int


class Visitor(BaseModel):
    id: str
    name: str
    purpose: str
    date: str
    timeIn: str
    timeOut: str | None
    status: str
    contactNumber: str
    hostName: str
    hostUnit: str
    approvedBy: str | None


VisitorActionResponse = VisitorResponse


class AccessPoint(BaseModel):
    id: str
    name: str
    type: str
    location: str
    status: str
    lastAccess: str
    accessCount: int
    restrictions: list[str]


class AccessLog(BaseModel):
    id: str
    accessPoint: str
    personName: str
    personType: str
    accessType: str
    timestamp: str
    status: str
    method: str


class PatrolCheckpoint(BaseModel):
    id: int
    name: str
    location: str
    checkedAt: str | None
    status: str
    notes: str | None


class PatrolRound(BaseModel):
    id: str
    guardName: str
    startTime: str
    endTime: str | None
    status: str
    route: str
    checkpoints: list[PatrolCheckpoint]
    incidents: int
    notes: str | None


class PatrolRoute(BaseModel):
    id: str
    name: str
    description: str
    estimatedDuration: int
    checkpoints: list[str]
    priority: str
    isActive: bool


class PatrolRouteCheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    order_index: int


class PatrolRouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    building_id: UUID
    is_active: bool
    checkpoints: list[PatrolRouteCheckpointResponse]
    created_at: datetime
    updated_at: datetime


class PatrolRoundCheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    checkpoint_id: UUID
    checkpoint_name: str
    order_index: int
    is_visited: bool
    visited_at: datetime | None
    notes: str | None


class PatrolRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guard_id: UUID
    route_id: UUID
    route_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    notes: str | None
    checkpoints: list[PatrolRoundCheckpointResponse]
    total_checkpoints: int
    visited_checkpoints: int
    created_at: datetime
    updated_at: datetime


class StartPatrolRoundRequest(BaseModel):
    route_id: UUID
    notes: str | None = None


class CheckpointVisitRequest(BaseModel):
    notes: str | None = None


class Incident(BaseModel):
    id: str
    title: str
    description: str
    type: str
    severity: str
    location: str
    reportedBy: str
    reportedAt: str
    status: str
    assignedTo: str | None
    resolvedAt: str | None
    resolution: str | None
    attachments: list[str] | None


class SecurityLog(BaseModel):
    id: str
    timestamp: str
    type: str
    category: str
    description: str
    severity: str
    source: str
    details: dict | None
    userId: str | None
    ipAddress: str | None


class SecurityReport(BaseModel):
    id: str
    title: str
    type: str
    generatedAt: str
    generatedBy: str
    period: dict
    summary: dict
    fileUrl: str | None


class EntryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_name: str
    resident_name: str
    unit_number: str | None
    status: str
    check_in_time: datetime | None
    check_out_time: datetime | None
    logged_at: datetime
    approved_by_name: str | None
    purpose: str | None
