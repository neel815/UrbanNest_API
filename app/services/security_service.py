import json
from datetime import date, datetime, time, timezone
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AccessLog,
    AccessPoint,
    Announcement,
    Incident,
    PatrolStatus,
    PatrolRoundCheckpoint,
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
from app.models.security import SecurityProfile
from app.schemas.resident import AnnouncementResponse
from app.schemas.security import (
    CheckpointVisitRequest,
    EntryLogResponse,
    PatrolRouteCheckpointResponse,
    PatrolRouteResponse,
    PatrolRoundCheckpointResponse,
    PatrolRoundResponse,
    StartPatrolRoundRequest,
)


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
        VisitorStatus.PENDING: "pending",
        VisitorStatus.APPROVED: "approved",
        VisitorStatus.CHECKED_IN: "checked_in",
        VisitorStatus.CHECKED_OUT: "checked_out",
        VisitorStatus.DENIED: "denied",
    }
    return mapping[status]


def _visitor_status_db(status: str) -> VisitorStatus:
    mapping = {
        "pending": VisitorStatus.PENDING,
        "approved": VisitorStatus.APPROVED,
        "checked_in": VisitorStatus.CHECKED_IN,
        "checked_out": VisitorStatus.CHECKED_OUT,
        "denied": VisitorStatus.DENIED,
    }
    return mapping[status]


def _get_visitor_for_security(db: Session, visitor_id: str | UUID, user_id: str | UUID) -> Visitor:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)
    visitor = (
        db.query(Visitor)
        .options(
            joinedload(Visitor.resident).joinedload(User.resident_profile).joinedload(ResidentProfile.unit),
            joinedload(Visitor.approved_by_user),
        )
        .filter(Visitor.id == _uuid(visitor_id))
        .first()
    )
    if not visitor:
        raise ValueError("Visitor not found")

    resident = visitor.resident
    resident_profile = resident.resident_profile if resident else None
    unit = resident_profile.unit if resident_profile else None
    resident_building_id = unit.building_id if unit else None

    if resident_building_id != building_id:
        raise PermissionError("Access denied. Visitor does not belong to your building")

    return visitor


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
        "hostName": resident.full_name if resident else "",
        "hostUnit": unit_number,
        "approvedBy": visitor.approved_by_user.full_name if visitor.approved_by_user else None,
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


def _checkpoint_uuid(route_id: UUID, order_index: int, name: str) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"urban-nest:patrol-route:{route_id}:{order_index}:{name}")


def _normalize_route_checkpoints(route: PatrolRoute) -> list[PatrolRouteCheckpointResponse]:
    checkpoint_rows = route.checkpoints if isinstance(route.checkpoints, list) else []
    checkpoints: list[PatrolRouteCheckpointResponse] = []
    # Build a list of (order_index, name) then sort deterministically
    annotated: list[tuple[int, str]] = []
    for idx, checkpoint in enumerate(checkpoint_rows, start=1):
        if isinstance(checkpoint, dict):
            order_index = int(checkpoint.get("order_index", idx))
            checkpoint_name = str(checkpoint.get("name", f"Checkpoint {idx}"))
        else:
            order_index = idx
            checkpoint_name = str(checkpoint)
        annotated.append((order_index, checkpoint_name))

    annotated.sort(key=lambda t: t[0])
    for order_index, checkpoint_name in annotated:
        checkpoints.append(
            PatrolRouteCheckpointResponse(
                id=_checkpoint_uuid(route.id, order_index, checkpoint_name),
                name=checkpoint_name,
                order_index=order_index,
            )
        )
    checkpoints.sort(key=lambda checkpoint: checkpoint.order_index)
    return checkpoints


def _serialize_patrol_route(route: PatrolRoute) -> PatrolRouteResponse:
    return PatrolRouteResponse(
        id=route.id,
        name=route.name,
        description=route.description,
        building_id=route.building_id,
        is_active=route.is_active,
        checkpoints=_normalize_route_checkpoints(route),
        created_at=route.created_at,
        updated_at=route.updated_at,
    )


def _serialize_patrol_round_checkpoint(checkpoint: PatrolRoundCheckpoint) -> PatrolRoundCheckpointResponse:
    return PatrolRoundCheckpointResponse(
        id=checkpoint.id,
        checkpoint_id=checkpoint.checkpoint_id,
        checkpoint_name=checkpoint.checkpoint_name,
        order_index=checkpoint.order_index,
        is_visited=checkpoint.is_visited,
        visited_at=checkpoint.visited_at,
        notes=checkpoint.notes,
    )


def _serialize_patrol_round(round_: PatrolRound) -> PatrolRoundResponse:
    route = round_.route
    checkpoints = list(round_.checkpoints or [])
    visited_checkpoints = sum(1 for checkpoint in checkpoints if checkpoint.is_visited)
    status = round_.status.value
    if status == PatrolStatus.CANCELLED.value:
        status = "abandoned"
    return PatrolRoundResponse(
        id=round_.id,
        guard_id=round_.guard_id,
        route_id=round_.route_id,
        route_name=route.name if route else "",
        status=status,
        started_at=round_.started_at,
        completed_at=round_.completed_at,
        notes=round_.notes,
        checkpoints=[_serialize_patrol_round_checkpoint(checkpoint) for checkpoint in checkpoints],
        total_checkpoints=len(checkpoints),
        visited_checkpoints=visited_checkpoints,
        created_at=round_.created_at,
        updated_at=round_.updated_at,
    )


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


def _get_security_building_id(db: Session, user_id: UUID) -> UUID:
    profile = db.query(SecurityProfile).filter(SecurityProfile.user_id == user_id).first()
    if not profile or profile.assigned_building_id is None:
        raise ValueError("Security profile not assigned to any building")
    return profile.assigned_building_id


def get_dashboard_stats(db: Session, user_id: str | UUID) -> dict:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)
    today_start = _today_start()

    resident_ids_query = (
        db.query(ResidentProfile.user_id)
        .join(ResidentProfile.unit)
        .filter(ResidentProfile.unit_id.isnot(None), ResidentProfile.unit.has(building_id=building_id))
    )

    active_visitors = (
        db.query(func.count(Visitor.id))
        .filter(Visitor.resident_id.in_(resident_ids_query), Visitor.status == VisitorStatus.CHECKED_IN)
        .scalar()
        or 0
    )
    pending_approvals = (
        db.query(func.count(Visitor.id))
        .filter(Visitor.resident_id.in_(resident_ids_query), Visitor.status == VisitorStatus.PENDING)
        .scalar()
        or 0
    )
    incidents_today = (
        db.query(func.count(Incident.id))
        .filter(Incident.reported_by == parsed_user_id, Incident.created_at >= today_start)
        .scalar()
        or 0
    )
    patrol_rounds = (
        db.query(func.count(PatrolRound.id))
        .filter(PatrolRound.guard_id == parsed_user_id, PatrolRound.status == PatrolStatus.IN_PROGRESS)
        .scalar()
        or 0
    )
    access_alerts = (
        db.query(func.count(AccessLog.id))
        .join(AccessLog.access_point)
        .filter(AccessPoint.building_id == building_id, AccessLog.timestamp >= today_start)
        .scalar()
        or 0
    )
    total_entries = (
        db.query(func.count(AccessLog.id))
        .join(AccessLog.access_point)
        .filter(AccessPoint.building_id == building_id, AccessLog.timestamp >= today_start)
        .scalar()
        or 0
    )

    return {
        "activeVisitors": active_visitors,
        "pendingApprovals": pending_approvals,
        "incidentsToday": incidents_today,
        "patrolRounds": patrol_rounds,
        "accessAlerts": access_alerts,
        "totalEntries": total_entries,
    }


def get_announcements(db: Session, user_id: str | UUID) -> list[AnnouncementResponse]:
    building_id = _get_security_building_id(db, _uuid(user_id))
    records = (
        db.query(Announcement)
        .filter(Announcement.building_id == building_id)
        .order_by(Announcement.published_at.desc(), Announcement.created_at.desc())
        .all()
    )
    return [AnnouncementResponse.model_validate(record) for record in records]


def get_visitors(db: Session, user_id: str | UUID) -> list[dict]:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)

    resident_ids_query = (
        db.query(ResidentProfile.user_id)
        .join(ResidentProfile.unit)
        .filter(ResidentProfile.unit_id.isnot(None), ResidentProfile.unit.has(building_id=building_id))
    )

    visitors = (
        db.query(Visitor)
        .options(
            joinedload(Visitor.resident).joinedload(User.resident_profile).joinedload(ResidentProfile.unit),
            joinedload(Visitor.approved_by_user),
        )
        .filter(Visitor.resident_id.in_(resident_ids_query))
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
        check_in_time=None,
        check_out_time=None,
        status=status,
        approved_by=None,
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

    guard_building_id = _get_security_building_id(db, current_user.id)
    resident = visitor.resident
    resident_profile = resident.resident_profile if resident else None
    unit = resident_profile.unit if resident_profile else None
    visitor_building_id = unit.building_id if unit else None

    if visitor_building_id != guard_building_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This visitor does not belong to your building")

    visitor.status = _visitor_status_db(status)
    visitor.approved_by = current_user.id
    if visitor.status == VisitorStatus.CHECKED_IN and visitor.check_in_time is None:
        visitor.check_in_time = datetime.now(timezone.utc)
    if visitor.status == VisitorStatus.CHECKED_OUT:
        visitor.check_out_time = datetime.now(timezone.utc)

    db.commit()
    db.refresh(visitor)
    return _serialize_visitor(visitor)


def approve_visitor(db: Session, visitor_id: str | UUID, user_id: str | UUID) -> Visitor:
    visitor = _get_visitor_for_security(db, visitor_id, user_id)
    if visitor.status != VisitorStatus.PENDING:
        raise ValueError("Only pending visitors can be approved")

    visitor.status = VisitorStatus.APPROVED
    visitor.approved_by = _uuid(user_id)
    db.commit()
    db.refresh(visitor)
    return visitor


def deny_visitor(db: Session, visitor_id: str | UUID, user_id: str | UUID) -> Visitor:
    visitor = _get_visitor_for_security(db, visitor_id, user_id)
    if visitor.status != VisitorStatus.PENDING:
        raise ValueError("Only pending visitors can be denied")

    visitor.status = VisitorStatus.DENIED
    visitor.approved_by = _uuid(user_id)
    db.commit()
    db.refresh(visitor)
    return visitor


def checkin_visitor(db: Session, visitor_id: str | UUID, user_id: str | UUID) -> Visitor:
    visitor = _get_visitor_for_security(db, visitor_id, user_id)
    if visitor.status != VisitorStatus.APPROVED:
        raise ValueError("Visitor must be approved before check-in")

    visitor.status = VisitorStatus.CHECKED_IN
    visitor.check_in_time = datetime.utcnow()
    db.commit()
    db.refresh(visitor)
    return visitor


def checkout_visitor(db: Session, visitor_id: str | UUID, user_id: str | UUID) -> Visitor:
    visitor = _get_visitor_for_security(db, visitor_id, user_id)
    if visitor.status != VisitorStatus.CHECKED_IN:
        raise ValueError("Visitor must be checked in before check-out")

    visitor.status = VisitorStatus.CHECKED_OUT
    visitor.check_out_time = datetime.utcnow()
    db.commit()
    db.refresh(visitor)
    return visitor


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


def get_access_logs(db: Session, user_id: str | UUID) -> list[dict]:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)

    logs = (
        db.query(AccessLog)
        .options(joinedload(AccessLog.access_point), joinedload(AccessLog.user))
        .join(AccessLog.access_point)
        .filter(AccessPoint.building_id == building_id)
        .order_by(AccessLog.timestamp.desc())
        .all()
    )
    return [_serialize_access_log(log) for log in logs]


def _serialize_entry_log(visitor: Visitor) -> EntryLogResponse:
    resident = visitor.resident
    resident_profile = resident.resident_profile if resident else None
    unit = resident_profile.unit if resident_profile else None
    logged_at = visitor.check_in_time or visitor.check_out_time or visitor.created_at
    return EntryLogResponse(
        id=visitor.id,
        visitor_name=visitor.visitor_name,
        resident_name=resident.full_name if resident else "",
        unit_number=unit.unit_number if unit else None,
        status=visitor.status.value,
        check_in_time=visitor.check_in_time,
        check_out_time=visitor.check_out_time,
        logged_at=logged_at,
        approved_by_name=visitor.approved_by_user.full_name if visitor.approved_by_user else None,
        purpose=visitor.purpose,
    )


def get_entry_logs(db: Session, user_id: str | UUID) -> list[EntryLogResponse]:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)

    resident_ids_query = (
        db.query(ResidentProfile.user_id)
        .join(ResidentProfile.unit)
        .filter(ResidentProfile.unit_id.isnot(None), ResidentProfile.unit.has(building_id=building_id))
    )

    logs = (
        db.query(Visitor)
        .options(
            joinedload(Visitor.resident).joinedload(User.resident_profile).joinedload(ResidentProfile.unit),
            joinedload(Visitor.approved_by_user),
        )
        .filter(
            Visitor.resident_id.in_(resident_ids_query),
            Visitor.status.in_([VisitorStatus.CHECKED_IN, VisitorStatus.CHECKED_OUT, VisitorStatus.DENIED]),
        )
        .order_by(func.coalesce(Visitor.check_in_time, Visitor.check_out_time, Visitor.created_at).desc())
        .all()
    )
    return [_serialize_entry_log(log) for log in logs]


def toggle_access_point(db: Session, point_id: str | UUID, user_id: str | UUID) -> dict:
    guard_building_id = _get_security_building_id(db, _uuid(user_id))
    point = db.query(AccessPoint).filter(AccessPoint.id == _uuid(point_id)).first()
    if not point:
        raise ValueError("Access point not found")
    if point.building_id != guard_building_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This access point does not belong to your building")

    point.is_active = not point.is_active
    db.commit()
    db.refresh(point)
    access_count = db.query(func.count(AccessLog.id)).filter(AccessLog.access_point_id == point.id).scalar() or 0
    last_access = db.query(func.max(AccessLog.timestamp)).filter(AccessLog.access_point_id == point.id).scalar()
    return _serialize_access_point(point, int(access_count), last_access)


def get_patrol_rounds(db: Session, user_id: str | UUID) -> list[PatrolRoundResponse]:
    parsed_user_id = _uuid(user_id)

    rounds = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route), joinedload(PatrolRound.checkpoints))
        .filter(PatrolRound.guard_id == parsed_user_id)
        .order_by(PatrolRound.started_at.desc())
        .all()
    )
    return [_serialize_patrol_round(round_) for round_ in rounds]


def get_patrol_routes(db: Session, user_id: str | UUID) -> list[PatrolRouteResponse]:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)
    routes = (
        db.query(PatrolRoute)
        .filter(PatrolRoute.building_id == building_id, PatrolRoute.is_active.is_(True))
        .order_by(PatrolRoute.name.asc(), PatrolRoute.created_at.desc())
        .all()
    )
    return [_serialize_patrol_route(route) for route in routes]


def start_patrol_round(db: Session, user_id: str | UUID, data: StartPatrolRoundRequest) -> PatrolRoundResponse:
    parsed_user_id = _uuid(user_id)
    building_id = _get_security_building_id(db, parsed_user_id)
    active_round = (
        db.query(PatrolRound)
        .filter(PatrolRound.guard_id == parsed_user_id, PatrolRound.status == PatrolStatus.IN_PROGRESS)
        .first()
    )
    if active_round:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete your current round first")

    route = db.query(PatrolRoute).filter(PatrolRoute.id == data.route_id).first()
    if not route:
        raise ValueError("Patrol route not found")
    if route.building_id != building_id:
        raise ValueError("Patrol route does not belong to your building")
    if not route.is_active:
        raise ValueError("Patrol route is inactive")

    route_checkpoints = _normalize_route_checkpoints(route)
    patrol_round = PatrolRound(
        guard_id=parsed_user_id,
        route_id=route.id,
        started_at=datetime.now(timezone.utc),
        status=PatrolStatus.IN_PROGRESS,
        notes=data.notes,
    )
    db.add(patrol_round)
    db.flush()

    for checkpoint in route_checkpoints:
        db.add(
            PatrolRoundCheckpoint(
                round_id=patrol_round.id,
                checkpoint_id=checkpoint.id,
                checkpoint_name=checkpoint.name,
                order_index=checkpoint.order_index,
                is_visited=False,
            )
        )

    db.commit()
    patrol_round = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route), joinedload(PatrolRound.checkpoints))
        .filter(PatrolRound.id == patrol_round.id)
        .first()
    )
    if patrol_round is None:
        raise ValueError("Patrol round not found")
    return _serialize_patrol_round(patrol_round)

def mark_checkpoint_visited(
    db: Session,
    user_id: str | UUID,
    round_id: str | UUID,
    checkpoint_id: str | UUID,
    data: CheckpointVisitRequest,
) -> PatrolRoundResponse:
    parsed_user_id = _uuid(user_id)
    patrol_round = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route), joinedload(PatrolRound.checkpoints))
        .filter(PatrolRound.id == _uuid(round_id))
        .first()
    )
    if not patrol_round:
        raise ValueError("Patrol round not found")
    if patrol_round.guard_id != parsed_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only complete your own patrol rounds")
    if patrol_round.status != PatrolStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This round is no longer in progress")

    parsed_checkpoint_id = _uuid(checkpoint_id)
    checkpoint = (
        db.query(PatrolRoundCheckpoint)
        .filter(
            PatrolRoundCheckpoint.round_id == patrol_round.id,
            PatrolRoundCheckpoint.checkpoint_id == parsed_checkpoint_id,
        )
        .first()
    )
    if not checkpoint:
        raise ValueError("Checkpoint not found")

    checkpoint.is_visited = True
    checkpoint.visited_at = datetime.now(timezone.utc)
    if data.notes is not None:
        checkpoint.notes = data.notes

    db.commit()
    refreshed_round = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route), joinedload(PatrolRound.checkpoints))
        .filter(PatrolRound.id == patrol_round.id)
        .first()
    )
    if refreshed_round is None:
        raise ValueError("Patrol round not found")
    return _serialize_patrol_round(refreshed_round)


def complete_patrol_round(db: Session, round_id: str | UUID, user_id: str | UUID) -> PatrolRoundResponse:
    patrol_round = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route), joinedload(PatrolRound.checkpoints))
        .filter(PatrolRound.id == _uuid(round_id))
        .first()
    )
    if not patrol_round:
        raise ValueError("Patrol round not found")
    if patrol_round.guard_id != _uuid(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only complete your own patrol rounds")
    if patrol_round.status == PatrolStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This round has already been completed")

    incomplete_checkpoints = [checkpoint for checkpoint in patrol_round.checkpoints if not checkpoint.is_visited]
    if incomplete_checkpoints:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete all checkpoints before finishing the round")

    patrol_round.completed_at = datetime.now(timezone.utc)
    patrol_round.status = PatrolStatus.COMPLETED
    db.commit()
    refreshed_round = (
        db.query(PatrolRound)
        .options(joinedload(PatrolRound.guard), joinedload(PatrolRound.route), joinedload(PatrolRound.checkpoints))
        .filter(PatrolRound.id == patrol_round.id)
        .first()
    )
    if refreshed_round is None:
        raise ValueError("Patrol round not found")
    return _serialize_patrol_round(refreshed_round)


def check_checkpoint(db: Session, round_id: str | UUID, checkpoint_id: int, data: dict, user_id: str | UUID) -> dict:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use the checkpoint visit endpoint")


def get_incidents(db: Session, user_id: str | UUID) -> list[dict]:
    parsed_user_id = _uuid(user_id)
    incidents = (
        db.query(Incident)
        .options(joinedload(Incident.reporter))
        .filter(Incident.reported_by == parsed_user_id)
        .order_by(Incident.created_at.desc())
        .all()
    )
    return [_serialize_incident(incident) for incident in incidents]


def create_incident(db: Session, current_user: User, payload: dict) -> dict:
    _get_security_building_id(db, current_user.id)
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


def update_incident_status(db: Session, user_id: str | UUID, incident_id: str | UUID, payload: dict) -> dict:
    guard_building_id = _get_security_building_id(db, _uuid(user_id))
    incident = db.query(Incident).filter(Incident.id == _uuid(incident_id)).first()
    if not incident:
        raise ValueError("Incident not found")

    if incident.reported_by is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot update this incident")

    if getattr(incident, "building_id", None) is not None:
        if incident.building_id != guard_building_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot update this incident")
    elif incident.reported_by != _uuid(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot update this incident")

    incident.status = SecurityIncidentStatus(payload.get("status", incident.status.value))
    db.commit()
    db.refresh(incident)
    db.refresh(incident, attribute_names=["reporter"])
    serialized = _serialize_incident(incident)
    serialized["assignedTo"] = incident.reporter.full_name if incident.reporter else None
    if incident.status in {SecurityIncidentStatus.RESOLVED, SecurityIncidentStatus.CLOSED}:
        serialized["resolvedAt"] = datetime.now(timezone.utc).isoformat()
    serialized["resolution"] = payload.get("resolution")
    return serialized


def get_security_reports(db: Session, user_id: str | UUID) -> list[dict]:
    parsed_user_id = _uuid(user_id)
    reports = (
        db.query(SecurityReport)
        .options(joinedload(SecurityReport.creator))
        .filter(SecurityReport.created_by == parsed_user_id)
        .order_by(SecurityReport.created_at.desc())
        .all()
    )
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
