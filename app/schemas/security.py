from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.security import SecurityShift


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
    vehicleNumber: str | None
    hostName: str
    hostUnit: str
    approvedBy: str | None
    notes: str | None


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
