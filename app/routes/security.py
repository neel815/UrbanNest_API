from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services import security_service
from app.services.auth_service import get_current_user


router = APIRouter()


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


def _service_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    status_code = 404 if "not found" in message.lower() else 400
    return HTTPException(status_code=status_code, detail=message)


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_dashboard_stats(db)


@router.get("/visitors")
async def get_visitors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_visitors(db)


@router.post("/visitors")
async def create_visitor(
    visitor: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.create_visitor(db, current_user, visitor)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/visitors/{visitor_id}")
async def update_visitor_status(
    visitor_id: UUID,
    status_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.update_visitor_status(
            db,
            current_user,
            visitor_id,
            status_update.get("status", "expected"),
        )
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/access-points")
async def get_access_points(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_access_points(db)


@router.get("/access-logs")
async def get_access_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_access_logs(db)


@router.patch("/access-points/{point_id}/toggle")
async def toggle_access_point(
    point_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.toggle_access_point(db, point_id)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/patrol-rounds")
async def get_patrol_rounds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_patrol_rounds(db)


@router.get("/patrol-routes")
async def get_patrol_routes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_patrol_routes(db)


@router.post("/patrol-rounds")
async def start_patrol_round(
    patrol_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.start_patrol_round(db, current_user, patrol_data)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/patrol-rounds/{round_id}/complete")
async def complete_patrol_round(
    round_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.complete_patrol_round(db, round_id)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.post("/patrol-rounds/{round_id}/checkpoints/{checkpoint_id}")
async def check_checkpoint(
    round_id: UUID,
    checkpoint_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.check_checkpoint(db, round_id, checkpoint_id, data)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/incidents")
async def get_incidents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_incidents(db)


@router.post("/incidents")
async def create_incident(
    incident: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.create_incident(db, current_user, incident)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/incidents/{incident_id}")
async def update_incident_status(
    incident_id: UUID,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.update_incident_status(db, current_user, incident_id, update_data)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/logs")
async def get_security_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_access_logs(db)


@router.get("/reports")
async def get_security_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return security_service.get_security_reports(db)


@router.post("/reports")
async def generate_report(
    report_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return security_service.generate_report(db, current_user, report_data)
    except ValueError as exc:
        raise _service_error(exc) from exc
