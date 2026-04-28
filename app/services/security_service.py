import json
from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AccessLog,
    AccessPoint,
    Incident,
    PatrolStatus,
    PatrolRound,
    PatrolRoute,
    ResidentProfile,
    SecurityIncidentCategory,
    SecurityIncidentSeverity,
    SecurityIncidentStatus,
    SecurityReport,
    Visitor,
    VisitorStatus,
)
from app.models.user import User, UserRole


def _uuid(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _today_start() -> datetime:
    current = datetime.now(timezone.utc)
    return datetime.combine(current.date(), time.min, tzinfo=timezone.utc)


def _serialize_uuid(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def _serialize_timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _visitor_status_label(status: VisitorStatus) -> str:
    mapping = {
        VisitorStatus.PENDING: "expected",
        VisitorStatus.APPROVED: "expected",
        VisitorStatus.CHECKED_IN: "checked_in",
        VisitorStatus.CHECKED_OUT: "checked_out",
        VisitorStatus.DENIED: "rejected",
    }
    return mapping[status]


def _visitor_status_db(status: str) -> VisitorStatus:
    mapping = {
        "expected": VisitorStatus.PENDING,
        "checked_in": VisitorStatus.CHECKED_IN,
        "checked_out": VisitorStatus.CHECKED_OUT,
        "rejected": VisitorStatus.DENIED,
    }
    return mapping[status]


def _person_type_for_user(user: User | None) -> str:
    if user is None:
        return "visitor"
    if user.role == UserRole.RESIDENT:
        return "resident"
    if user.role == UserRole.SECURITY:
        return "staff"
    return "staff"


def _access_point_type(point: AccessPoint) -> str:
    text = f"{point.name} {point.location}".lower()
    if "parking" in text:
        return "parking"
    if "elevator" in text:
        return "elevator"
    if "door" in text:
        return "door"
    return "gate"


def _serialize_visitor(visitor: Visitor) -> dict:
    resident = visitor.resident
    resident_profile = resident.resident_profile if resident else None
    unit_number = resident_profile.unit.unit_number if resident_profile and resident_profile.unit else ""
    return {
        "id": str(visitor.id),
        "name": visitor.visitor_name,
        "purpose": visitor.purpose or "",
        "date": visitor.expected_date.isoformat(),
        "timeIn": visitor.check_in_time.strftime("%I:%M %p") if visitor.check_in_time else "",
        "timeOut": visitor.check_out_time.strftime("%I:%M %p") if visitor.check_out_time else None,
        "status": _visitor_status_label(visitor.status),
        "contactNumber": visitor.visitor_phone or "",
        "vehicleNumber": None,
        "hostName": resident.full_name if resident else "",
        "hostUnit": unit_number,
        "approvedBy": visitor.approved_by_user.full_name if visitor.approved_by_user else None,
        "notes": None,
    }


def _serialize_access_point(point: AccessPoint, access_count: int, last_access: datetime | None) -> dict:
    return {
        "id": str(point.id),
        "name": point.name,
        "type": _access_point_type(point),
        "location": point.location,
        "status": "active" if point.is_active else "inactive",
        "lastAccess": _serialize_timestamp(last_access) or "",
        "accessCount": access_count,
        "restrictions": [],
    }


def _serialize_access_log(log: AccessLog) -> dict:
    user = log.user
    return {
        "id": str(log.id),
        "accessPoint": log.access_point.name if log.access_point else "",
        "personName": user.full_name if user else "Unknown",
        "personType": _person_type_for_user(user),
        "accessType": log.direction.value,
        "timestamp": _serialize_timestamp(log.timestamp) or "",
        "status": "granted" if log.access_point and log.access_point.is_active else "denied",
        "method": "manual",
    }


def _serialize_patrol_route(route: PatrolRoute) -> dict:
    checkpoints = route.checkpoints if isinstance(route.checkpoints, list) else []
    checkpoint_names = []
    for checkpoint in checkpoints:
        if isinstance(checkpoint, dict):
            checkpoint_names.append(str(checkpoint.get("name", "Checkpoint")))
        else:
            checkpoint_names.append(str(checkpoint))
    return {
        "id": str(route.id),
        "name": route.name,
        "description": f"Patrol route for {route.name}",
        "estimatedDuration": max(len(checkpoint_names), 1) * 15,
        "checkpoints": checkpoint_names,
        "priority": "medium",
        "isActive": True,
    }


def _serialize_patrol_round(round_: PatrolRound) -> dict:
    route = round_.route
    route_checkpoints = route.checkpoints if route and isinstance(route.checkpoints, list) else []
    checkpoints = []
    for index, checkpoint in enumerate(route_checkpoints):
        checkpoint_name = checkpoint.get("name") if isinstance(checkpoint, dict) else str(checkpoint)
        checkpoints.append(
            {
                "id": index + 1,
                "name": checkpoint_name,
                "location": checkpoint.get("location", f"Location for {checkpoint_name}") if isinstance(checkpoint, dict) else f"Location for {checkpoint_name}",
                "checkedAt": checkpoint.get("checkedAt") if isinstance(checkpoint, dict) else None,
                "status": checkpoint.get("status", "pending") if isinstance(checkpoint, dict) else "pending",
                "notes": checkpoint.get("notes") if isinstance(checkpoint, dict) else None,
            }
        )
    return {
        "id": str(round_.id),
        "guardName": round_.guard.full_name if round_.guard else "",
        "startTime": _serialize_timestamp(round_.started_at) or "",
        "endTime": _serialize_timestamp(round_.completed_at),
        "status": round_.status.value,
        "route": route.name if route else "",
        "checkpoints": checkpoints,
        "incidents": 0,
        "notes": None,
    }


def _serialize_incident(incident: Incident) -> dict:
    reporter = incident.reporter
    return {
        "id": str(incident.id),
        "title": incident.title,
        "description": incident.description,
        "type": incident.category.value,
        "severity": incident.severity.value,
        "location": incident.location,
        "reportedBy": reporter.full_name if reporter else "",
        "reportedAt": _serialize_timestamp(incident.created_at) or "",
        "status": incident.status.value,
        "assignedTo": None,
        "resolvedAt": None,
        "resolution": None,
        "attachments": [],
    }


def _serialize_report(report: SecurityReport) -> dict:
    payload = {}
    if report.content:
        try:
            payload = json.loads(report.content)
        except json.JSONDecodeError:
            payload = {"content": report.content}
    return {
        "id": str(report.id),
        "title": report.title,
        "type": payload.get("type", "daily"),
        "generatedAt": _serialize_timestamp(report.created_at) or "",
        "generatedBy": report.creator.full_name if report.creator else "",
        "period": payload.get("period", {}),
        "summary": payload.get("summary", {}),
        "fileUrl": payload.get("fileUrl"),
    }


def get_dashboard_stats(db: Session) -> dict:
    today_start = _today_start()

    active_visitors = db.query(func.count(Visitor.id)).filter(Visitor.status == VisitorStatus.CHECKED_IN).scalar() or 0
    pending_approvals = db.query(func.count(Visitor.id)).filter(Visitor.status == VisitorStatus.PENDING).scalar() or 0
    incidents_today = db.query(func.count(Incident.id)).filter(Incident.created_at >= today_start).scalar() or 0
    patrol_rounds = db.query(func.count(PatrolRound.id)).filter(PatrolRound.status == PatrolStatus.IN_PROGRESS).scalar() or 0
    access_alerts = db.query(func.count(AccessLog.id)).filter(AccessLog.timestamp >= today_start).scalar() or 0
    total_entries = db.query(func.count(AccessLog.id)).filter(AccessLog.timestamp >= today_start).scalar() or 0

    return {
        "activeVisitors": active_visitors,
        "pendingApprovals": pending_approvals,
        "incidentsToday": incidents_today,
        "patrolRounds": patrol_rounds,
        "accessAlerts": access_alerts,
        "totalEntries": total_entries,
    }


def get_visitors(db: Session) -> list[dict]:
    visitors = (
        db.query(Visitor)
        .options(
            joinedload(Visitor.resident).joinedload(User.resident_profile).joinedload(ResidentProfile.unit),
            joinedload(Visitor.approved_by_user),
        )
        .order_by(Visitor.expected_date.desc(), Visitor.created_at.desc())
        .all()
    )
    return [_serialize_visitor(visitor) for visitor in visitors]


def create_visitor(db: Session, current_user: User, payload: dict) -> dict:
    host_name = payload.get("hostName", "").strip()
    host_unit = payload.get("hostUnit", "").strip()
    resident_query = db.query(User).filter(User.role == UserRole.RESIDENT, User.full_name == host_name)
    resident = resident_query.options(joinedload(User.resident_profile).joinedload("unit")).first()
    if not resident:
        raise ValueError("Host resident not found")
    if host_unit:
        resident_unit = resident.resident_profile.unit.unit_number if resident.resident_profile and resident.resident_profile.unit else None
        if resident_unit and resident_unit != host_unit:
            raise ValueError("Host unit does not match the selected resident")

    status = VisitorStatus.PENDING
    visitor = Visitor(
        visitor_name=payload.get("name", "").strip(),
        visitor_phone=payload.get("contactNumber"),
        purpose=payload.get("purpose"),
        resident_id=resident.id,
        expected_date=date.fromisoformat(payload.get("date") or datetime.now(timezone.utc).date().isoformat()),
        check_in_time=datetime.now(timezone.utc),
        status=status,
        approved_by=current_user.id,
    )
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return _serialize_visitor(visitor)


def update_visitor_status(db: Session, current_user: User, visitor_id: str | UUID, status: str) -> dict:
    visitor = (
        db.query(Visitor)
        .options(joinedload(Visitor.resident).joinedload(User.resident_profile).joinedload(ResidentProfile.unit), joinedload(Visitor.approved_by_user))
        .filter(Visitor.id == _uuid(visitor_id))
        .first()
    )
    if not visitor:
        raise ValueError("Visitor not found")

    visitor.status = _visitor_status_db(status)
    visitor.approved_by = current_user.id
    if visitor.status == VisitorStatus.CHECKED_IN and visitor.check_in_time is None:
        visitor.check_in_time = datetime.now(timezone.utc)
    if visitor.status == VisitorStatus.CHECKED_OUT:
        visitor.check_out_time = datetime.now(timezone.utc)

    db.commit()
    db.refresh(visitor)
    return _serialize_visitor(visitor)


def get_access_points(db: Session) -> list[dict]:
    points = db.query(AccessPoint).order_by(AccessPoint.name.asc()).all()
    if not points:
        return []

    access_counts = dict(
        db.query(AccessLog.access_point_id, func.count(AccessLog.id))
        .group_by(AccessLog.access_point_id)
        .all()
    )
    last_access_rows = dict(
        db.query(AccessLog.access_point_id, func.max(AccessLog.timestamp))
        .group_by(AccessLog.access_point_id)
        .all()
    )

    return [
        _serialize_access_point(
            point,
            int(access_counts.get(point.id, 0)),
            last_access_rows.get(point.id),
        )
        for point in points
    ]


def get_access_logs(db: Session) -> list[dict]:
    logs = (
        db.query(AccessLog)
        .options(joinedload(AccessLog.access_point), joinedload(AccessLog.user))
        .order_by(AccessLog.timestamp.desc())
        .all()
    )
    return [_serialize_access_log(log) for log in logs]


def toggle_access_point(db: Session, point_id: str | UUID) -> dict:
    point = db.query(AccessPoint).filter(AccessPoint.id == _uuid(point_id)).first()
    if not point:
        raise ValueError("Access point not found")

    point.is_active = not point.is_active
    db.commit()
    db.refresh(point)
    access_count = db.query(func.count(AccessLog.id)).filter(AccessLog.access_point_id == point.id).scalar() or 0
    last_access = db.query(func.max(AccessLog.timestamp)).filter(AccessLog.access_point_id == point.id).scalar()
    return _serialize_access_point(point, int(access_count), last_access)


def get_patrol_rounds(db: Session) -> list[dict]:
    rounds = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route))
        .order_by(PatrolRound.started_at.desc())
        .all()
    )
    return [_serialize_patrol_round(round_) for round_ in rounds]


def get_patrol_routes(db: Session) -> list[dict]:
    routes = db.query(PatrolRoute).order_by(PatrolRoute.name.asc()).all()
    return [_serialize_patrol_route(route) for route in routes]


def start_patrol_round(db: Session, current_user: User, patrol_data: dict) -> dict:
    route = db.query(PatrolRoute).filter(PatrolRoute.id == _uuid(patrol_data.get("routeId"))).first()
    if not route:
        raise ValueError("Patrol route not found")

    patrol_round = PatrolRound(
        guard_id=current_user.id,
        route_id=route.id,
        started_at=datetime.now(timezone.utc),
        status=PatrolStatus.IN_PROGRESS,
    )
    db.add(patrol_round)
    db.commit()
    db.refresh(patrol_round)
    return _serialize_patrol_round(patrol_round)


def complete_patrol_round(db: Session, round_id: str | UUID) -> dict:
    patrol_round = db.query(PatrolRound).filter(PatrolRound.id == _uuid(round_id)).first()
    if not patrol_round:
        raise ValueError("Patrol round not found")

    patrol_round.completed_at = datetime.now(timezone.utc)
    patrol_round.status = PatrolStatus.COMPLETED
    db.commit()
    db.refresh(patrol_round)
    return _serialize_patrol_round(patrol_round)


def check_checkpoint(db: Session, round_id: str | UUID, checkpoint_id: int, data: dict) -> dict:
    patrol_round = db.query(PatrolRound).filter(PatrolRound.id == _uuid(round_id)).first()
    if not patrol_round:
        raise ValueError("Patrol round not found")

    round_payload = _serialize_patrol_round(patrol_round)
    for checkpoint in round_payload["checkpoints"]:
        if checkpoint["id"] == checkpoint_id:
            checkpoint["checkedAt"] = datetime.now(timezone.utc).isoformat()
            checkpoint["status"] = "checked"
            checkpoint["notes"] = data.get("notes")
            break
    return {"id": round_payload["id"], "checkpoints": round_payload["checkpoints"]}


def get_incidents(db: Session) -> list[dict]:
    incidents = db.query(Incident).options(joinedload(Incident.reporter)).order_by(Incident.created_at.desc()).all()
    return [_serialize_incident(incident) for incident in incidents]


def create_incident(db: Session, current_user: User, payload: dict) -> dict:
    incident = Incident(
        title=payload.get("title", "").strip(),
        description=payload.get("description", "").strip(),
        category=SecurityIncidentCategory(payload.get("type", "security")),
        severity=SecurityIncidentSeverity(payload.get("severity", "medium")),
        location=payload.get("location", "").strip(),
        reported_by=current_user.id,
        status=SecurityIncidentStatus.OPEN,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    db.refresh(incident, attribute_names=["reporter"])
    return _serialize_incident(incident)


def update_incident_status(db: Session, current_user: User, incident_id: str | UUID, payload: dict) -> dict:
    incident = db.query(Incident).filter(Incident.id == _uuid(incident_id)).first()
    if not incident:
        raise ValueError("Incident not found")

    incident.status = SecurityIncidentStatus(payload.get("status", incident.status.value))
    db.commit()
    db.refresh(incident)
    db.refresh(incident, attribute_names=["reporter"])
    serialized = _serialize_incident(incident)
    serialized["assignedTo"] = current_user.full_name
    if incident.status in {SecurityIncidentStatus.RESOLVED, SecurityIncidentStatus.CLOSED}:
        serialized["resolvedAt"] = datetime.now(timezone.utc).isoformat()
    serialized["resolution"] = payload.get("resolution")
    return serialized


def get_security_reports(db: Session) -> list[dict]:
    reports = db.query(SecurityReport).options(joinedload(SecurityReport.creator)).order_by(SecurityReport.created_at.desc()).all()
    return [_serialize_report(report) for report in reports]


def generate_report(db: Session, current_user: User, payload: dict) -> dict:
    report_type = payload.get("type", "daily")
    period = {
        "start": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
        "end": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999).isoformat(),
    }
    summary = {
        "totalIncidents": db.query(func.count(Incident.id)).scalar() or 0,
        "totalVisitors": db.query(func.count(Visitor.id)).scalar() or 0,
        "totalPatrols": db.query(func.count(PatrolRound.id)).scalar() or 0,
        "totalAlerts": db.query(func.count(AccessLog.id)).scalar() or 0,
    }
    report = SecurityReport(
        title=f"{report_type.title()} Security Report - {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        content=json.dumps({"type": report_type, "period": period, "summary": summary, "fileUrl": f"/api/security/reports/placeholder/download"}),
        created_by=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    serialized = _serialize_report(report)
    serialized["period"] = period
    serialized["summary"] = summary
    serialized["fileUrl"] = f"/api/security/reports/{serialized['id']}/download"
    report.content = json.dumps({"type": report_type, "period": period, "summary": summary, "fileUrl": serialized["fileUrl"]})
    db.commit()
    db.refresh(report)
    return serialized
