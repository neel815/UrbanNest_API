from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resident import AnnouncementResponse, VisitorResponse
from app.schemas.security import (
    DashboardStats,
    Visitor,
    AccessPoint,
    AccessLog,
    PatrolCheckpoint,
    PatrolRound,
    PatrolRoute,
    Incident,
    SecurityLog,
    SecurityReport,
)
from app.services import security_service
from app.services.auth_service import get_current_user


router = APIRouter()


def _service_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    status_code = 404 if "not found" in message.lower() else 400
    return HTTPException(status_code=status_code, detail=message)


def _require_security(current_user: User) -> None:
    if current_user.role.value != "security":
        raise HTTPException(status_code=403, detail="Access denied. Security role required.")


@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_dashboard_stats(db, current_user.id)


@router.get("/announcements", response_model=list[AnnouncementResponse])
async def get_announcements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.get_announcements(db, current_user.id)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/visitors", response_model=list[Visitor])
async def get_visitors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_visitors(db, current_user.id)


@router.post("/visitors", response_model=Visitor)
async def create_visitor(
    visitor: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.create_visitor(db, current_user, visitor)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/visitors/{visitor_id}", response_model=Visitor)
async def update_visitor_status(
    visitor_id: UUID,
    status_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.update_visitor_status(
            db,
            current_user,
            visitor_id,
            status_update.get("status", "expected"),
        )
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/visitors/{visitor_id}/approve", response_model=VisitorResponse)
async def approve_visitor(
    visitor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.approve_visitor(db, visitor_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/visitors/{visitor_id}/deny", response_model=VisitorResponse)
async def deny_visitor(
    visitor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.deny_visitor(db, visitor_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/visitors/{visitor_id}/checkin", response_model=VisitorResponse)
async def checkin_visitor(
    visitor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.checkin_visitor(db, visitor_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/visitors/{visitor_id}/checkout", response_model=VisitorResponse)
async def checkout_visitor(
    visitor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.checkout_visitor(db, visitor_id, current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/access-points", response_model=list[AccessPoint])
async def get_access_points(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_access_points(db)


@router.get("/access-logs", response_model=list[AccessLog])
async def get_access_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_access_logs(db, current_user.id)


@router.patch("/access-points/{point_id}/toggle", response_model=AccessPoint)
async def toggle_access_point(
    point_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.toggle_access_point(db, point_id, current_user.id)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/patrol-rounds", response_model=list[PatrolRound])
async def get_patrol_rounds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_patrol_rounds(db, current_user.id)


@router.get("/patrol-routes", response_model=list[PatrolRoute])
async def get_patrol_routes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_patrol_routes(db, current_user.id)


@router.post("/patrol-rounds", response_model=PatrolRound)
async def start_patrol_round(
    patrol_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.start_patrol_round(db, current_user, patrol_data)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/patrol-rounds/{round_id}/complete", response_model=PatrolRound)
async def complete_patrol_round(
    round_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.complete_patrol_round(db, round_id, current_user.id)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.post("/patrol-rounds/{round_id}/checkpoints/{checkpoint_id}", response_model=PatrolRound)
async def check_checkpoint(
    round_id: UUID,
    checkpoint_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.check_checkpoint(db, round_id, checkpoint_id, data, current_user.id)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/incidents", response_model=list[Incident])
async def get_incidents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_incidents(db, current_user.id)


@router.post("/incidents", response_model=Incident)
async def create_incident(
    incident: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.create_incident(db, current_user, incident)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.patch("/incidents/{incident_id}", response_model=Incident)
async def update_incident_status(
    incident_id: UUID,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.update_incident_status(db, current_user.id, incident_id, update_data)
    except ValueError as exc:
        raise _service_error(exc) from exc


@router.get("/logs", response_model=list[SecurityLog])
async def get_security_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_access_logs(db, current_user.id)


@router.get("/reports", response_model=list[SecurityReport])
async def get_security_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    return security_service.get_security_reports(db, current_user.id)


@router.post("/reports", response_model=SecurityReport)
async def generate_report(
    report_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_security(current_user)
    try:
        return security_service.generate_report(db, current_user, report_data)
    except ValueError as exc:
        raise _service_error(exc) from exc
