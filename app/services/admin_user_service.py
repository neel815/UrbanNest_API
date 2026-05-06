import uuid
from datetime import datetime, timedelta, timezone
import secrets
import logging

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.admin import Announcement, Building, BuildingType, Unit, UnitStatus
from app.models.resident import Event, MaintenanceRequest, MaintenanceStatus, ResidentProfile
from app.models.security import SecurityProfile
from app.models.user import User, UserRole
from app.models.admin import AdminProfile
from app.schemas.admin import (
    AnnouncementCreateRequest,
    AnnouncementResponse,
    EventCreateRequest,
    EventResponse,
    AdminBuildingInfoResponse,
    AdminDashboardStatsResponse,
    CreateManagedUserRequest,
    MaintenanceStatusUpdateRequest,
    UnitCreateRequest,
    UnitResponse,
    UnitUpdateRequest,
    InviteManagedUserRequest,
    InviteManagedUserResponse,
    ManagedUserResponse,
    UpdateManagedUserRequest,
)
from app.schemas.resident import MaintenanceRequestResponse
from app.utils.security import hash_password
from app.services.email_service import send_resident_invite, send_security_invite


logger = logging.getLogger(__name__)
def require_admin(current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


def get_admin_building_id(db: Session, user_id: uuid.UUID) -> uuid.UUID:
    admin_profile = db.query(AdminProfile).filter(AdminProfile.user_id == user_id).first()
    if not admin_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin not assigned to any building")
    if admin_profile.building_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin not assigned to any building")
    return admin_profile.building_id


def get_admin_dashboard_stats(db: Session, building_id: uuid.UUID | None = None) -> AdminDashboardStatsResponse:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    resident_query = db.query(func.count(ResidentProfile.id))
    security_query = db.query(func.count(SecurityProfile.id))
    resident_recent_query = db.query(func.count(ResidentProfile.id)).join(User, User.id == ResidentProfile.user_id).filter(
        User.created_at >= since
    )
    security_recent_query = db.query(func.count(SecurityProfile.id)).join(User, User.id == SecurityProfile.user_id).filter(
        User.created_at >= since
    )

    if building_id is not None:
        resident_query = resident_query.join(Unit, Unit.id == ResidentProfile.unit_id).filter(Unit.building_id == building_id)
        security_query = security_query.filter(SecurityProfile.assigned_building_id == building_id)
        resident_recent_query = resident_recent_query.join(Unit, Unit.id == ResidentProfile.unit_id).filter(
            Unit.building_id == building_id
        )
        security_recent_query = security_recent_query.filter(SecurityProfile.assigned_building_id == building_id)

    total_residents = resident_query.scalar() or 0
    total_security = security_query.scalar() or 0
    residents_joined_last_30_days = resident_recent_query.scalar() or 0
    security_joined_last_30_days = security_recent_query.scalar() or 0

    return AdminDashboardStatsResponse(
        total_residents=total_residents,
        total_security=total_security,
        total_managed_users=total_residents + total_security,
        residents_joined_last_30_days=residents_joined_last_30_days,
        security_joined_last_30_days=security_joined_last_30_days,
        building_id=str(building_id) if building_id is not None else None,
        building_name=(
            db.query(Building.name).filter(Building.id == building_id).scalar() if building_id is not None else None
        ),
    )


def get_security_overview(db: Session, building_id: uuid.UUID | None = None):
    """Return security overview counts for admin dashboard."""
    base_query = db
    total_query = base_query.query(func.count(SecurityProfile.id))
    on_duty_query = base_query.query(func.count(SecurityProfile.id))
    active_shifts_query = base_query.query(func.count(func.distinct(SecurityProfile.shift)))

    if building_id is not None:
        total_query = total_query.filter(SecurityProfile.assigned_building_id == building_id)
        on_duty_query = on_duty_query.filter(SecurityProfile.assigned_building_id == building_id)
        active_shifts_query = active_shifts_query.filter(SecurityProfile.assigned_building_id == building_id)

    total_security = total_query.scalar() or 0
    # Only count guards who are active and have completed the invited reset (must_reset_password == False)
    on_duty_now = (
        on_duty_query.join(User, User.id == SecurityProfile.user_id)
        .filter(SecurityProfile.is_active == True, User.must_reset_password == False)
        .scalar()
        or 0
    )
    active_shifts = (
        active_shifts_query.join(User, User.id == SecurityProfile.user_id)
        .filter(SecurityProfile.is_active == True, User.must_reset_password == False)
        .scalar()
        or 0
    )

    building_name = None
    if building_id is not None:
        building_name = db.query(Building.name).filter(Building.id == building_id).scalar()

    return {
        'total_security': total_security,
        'on_duty_now': on_duty_now,
        'active_shifts': active_shifts,
        'building_id': str(building_id) if building_id is not None else None,
        'building_name': building_name,
    }


def _serialize_user(user: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        role=user.role.value,
        profile_image=user.profile_image,
        created_at=user.created_at.isoformat(),
        must_reset_password=user.must_reset_password,
        is_active=None,
    )


def _serialize_unit(unit: Unit, resident_name: str | None = None) -> UnitResponse:
    return UnitResponse(
        id=str(unit.id),
        building_id=str(unit.building_id),
        unit_number=unit.unit_number,
        floor=unit.floor,
        plot_number=unit.plot_number,
        status=unit.status,
        resident_name=resident_name,
    )


def get_admin_building_info(db: Session, building_id: uuid.UUID) -> AdminBuildingInfoResponse:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    return AdminBuildingInfoResponse(
        building_id=str(building.id),
        building_name=building.name,
        building_type=building.building_type,
    )


def list_units_for_building(db: Session, building_id: uuid.UUID) -> list[UnitResponse]:
    rows = (
        db.query(Unit, User.full_name)
        .outerjoin(ResidentProfile, ResidentProfile.unit_id == Unit.id)
        .outerjoin(User, User.id == ResidentProfile.user_id)
        .filter(Unit.building_id == building_id)
        .order_by(Unit.floor.asc().nullslast(), Unit.unit_number.asc())
        .all()
    )
    return [_serialize_unit(unit, resident_name) for unit, resident_name in rows]


def create_unit_for_building(db: Session, building_id: uuid.UUID, payload: UnitCreateRequest) -> UnitResponse:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    existing_unit = (
        db.query(Unit)
        .filter(Unit.building_id == building_id, Unit.unit_number == payload.unit_number)
        .first()
    )
    if existing_unit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit number already exists in this building")

    floor, plot_number = _normalize_unit_location(building.building_type, payload.floor, payload.plot_number)

    unit = Unit(
        building_id=building_id,
        unit_number=payload.unit_number,
        floor=floor,
        plot_number=plot_number,
        status=payload.status,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return _serialize_unit(unit)


def update_unit_for_building(
    db: Session,
    building_id: uuid.UUID,
    unit_id: str,
    payload: UnitUpdateRequest,
) -> UnitResponse:
    try:
        parsed_unit_id = uuid.UUID(unit_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid unit id") from exc

    unit = (
        db.query(Unit)
        .filter(Unit.id == parsed_unit_id, Unit.building_id == building_id)
        .first()
    )
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    if payload.unit_number and payload.unit_number != unit.unit_number:
        existing_unit = (
            db.query(Unit)
            .filter(Unit.building_id == building_id, Unit.unit_number == payload.unit_number, Unit.id != unit.id)
            .first()
        )
        if existing_unit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit number already exists in this building")
        unit.unit_number = payload.unit_number

    floor = payload.floor if payload.floor is not None else unit.floor
    plot_number = payload.plot_number if payload.plot_number is not None else unit.plot_number
    floor, plot_number = _normalize_unit_location(building.building_type, floor, plot_number)
    unit.floor = floor
    unit.plot_number = plot_number
    if payload.status is not None:
        unit.status = payload.status

    db.commit()
    db.refresh(unit)

    resident_name = (
        db.query(User.full_name)
        .join(ResidentProfile, ResidentProfile.user_id == User.id)
        .filter(ResidentProfile.unit_id == unit.id)
        .scalar()
    )
    return _serialize_unit(unit, resident_name)


def delete_unit_for_building(db: Session, building_id: uuid.UUID, unit_id: str) -> dict:
    try:
        parsed_unit_id = uuid.UUID(unit_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid unit id") from exc

    unit = (
        db.query(Unit)
        .filter(Unit.id == parsed_unit_id, Unit.building_id == building_id)
        .first()
    )
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    resident_exists = db.query(ResidentProfile).filter(ResidentProfile.unit_id == unit.id).first()
    if unit.status == UnitStatus.OCCUPIED or resident_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit is occupied")

    db.delete(unit)
    db.commit()
    return {"message": "Unit deleted"}


def list_users_by_role(role: UserRole, db: Session, building_id: uuid.UUID | None = None) -> list[ManagedUserResponse]:
    if role == UserRole.RESIDENT:
        query = db.query(ResidentProfile).join(User, User.id == ResidentProfile.user_id)
        if building_id is not None:
            query = query.join(Unit, Unit.id == ResidentProfile.unit_id).filter(Unit.building_id == building_id)
        profiles = query.order_by(User.created_at.desc()).all()
        return [_serialize_user(profile.user) for profile in profiles]

    if role == UserRole.SECURITY:
        query = db.query(SecurityProfile).join(User, User.id == SecurityProfile.user_id)
        if building_id is not None:
            query = query.filter(SecurityProfile.assigned_building_id == building_id)
        profiles = query.order_by(User.created_at.desc()).all()
        # Include is_active from the security profile so frontend can render pending/active status
        result: list[ManagedUserResponse] = []
        for profile in profiles:
            user_model = profile.user
            serialized = ManagedUserResponse(
                id=str(user_model.id),
                full_name=user_model.full_name,
                email=user_model.email,
                phone_number=user_model.phone_number,
                role=user_model.role.value,
                profile_image=user_model.profile_image,
                created_at=user_model.created_at.isoformat(),
                must_reset_password=user_model.must_reset_password,
                is_active=profile.is_active,
            )
            result.append(serialized)
        return result

    users = db.query(User).filter(User.role == role).order_by(User.created_at.desc()).all()
    return [_serialize_user(user) for user in users]


def create_user_by_role(
    payload: CreateManagedUserRequest,
    role: UserRole,
    db: Session,
    building_id: uuid.UUID | None = None,
) -> ManagedUserResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
            phone_number=payload.phone_number,
        hashed_password=hash_password(payload.password),
        profile_image=payload.profile_image,
        role=role,
    )
    db.add(user)
    db.flush()

    if role == UserRole.RESIDENT:
        if payload.unit_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unit_id is required for residents")
        if building_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin building is required")
        try:
            parsed_unit_id = uuid.UUID(payload.unit_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid unit id") from exc

        unit = (
            db.query(Unit)
            .filter(Unit.id == parsed_unit_id, Unit.building_id == building_id)
            .first()
        )
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found in your building")
        if unit.status != UnitStatus.VACANT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit is not vacant")

        db.add(ResidentProfile(user_id=user.id, unit_id=unit.id))
        unit.status = UnitStatus.OCCUPIED
    elif role == UserRole.SECURITY:
        db.add(SecurityProfile(user_id=user.id, assigned_building_id=building_id))

    db.commit()
    db.refresh(user)
    return _serialize_user(user)


def invite_user_by_role(
    payload: InviteManagedUserRequest,
    role: UserRole,
    db: Session,
    building_id: uuid.UUID | None = None,
) -> InviteManagedUserResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    reset_token = secrets.token_urlsafe(32)
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone_number=payload.phone_number,
        hashed_password=hash_password(secrets.token_urlsafe(20)),
        profile_image=payload.profile_image,
        role=role,
        must_reset_password=True,
        reset_token=reset_token,
        reset_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(user)
    db.flush()

    if role == UserRole.RESIDENT:
        if payload.unit_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unit_id is required for residents")
        if building_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin building is required")
        try:
            parsed_unit_id = uuid.UUID(payload.unit_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid unit id") from exc

        unit = (
            db.query(Unit)
            .filter(Unit.id == parsed_unit_id, Unit.building_id == building_id)
            .first()
        )
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found in your building")
        if unit.status != UnitStatus.VACANT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit is not vacant")

        db.add(ResidentProfile(user_id=user.id, unit_id=unit.id))
        unit.status = UnitStatus.OCCUPIED
    elif role == UserRole.SECURITY:
        db.add(SecurityProfile(user_id=user.id, assigned_building_id=building_id))

    db.commit()

    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    
    # Send invitation email based on role
    try:
        if role == UserRole.RESIDENT:
            # Get unit and building info for resident email
            unit = db.query(Unit).filter(Unit.id == uuid.UUID(payload.unit_id)).first()
            building = db.query(Building).filter(Building.id == building_id).first() if building_id else None
            
            unit_number = unit.unit_number if unit else "Unassigned"
            building_name = building.name if building else "UrbanNest"
            
            send_resident_invite(
                to_email=payload.email,
                to_name=payload.full_name,
                building_name=building_name,
                unit_number=unit_number,
                setup_link=reset_link,
            )
        elif role == UserRole.SECURITY:
            # Get building info and shift for security email
            building = db.query(Building).filter(Building.id == building_id).first() if building_id else None
            security_profile = db.query(SecurityProfile).filter(SecurityProfile.user_id == user.id).first()
            
            building_name = building.name if building else "UrbanNest"
            shift = security_profile.shift if security_profile and security_profile.shift else "To be assigned"
            
            send_security_invite(
                to_email=payload.email,
                to_name=payload.full_name,
                building_name=building_name,
                shift=shift,
                setup_link=reset_link,
            )
    except Exception as e:
        logger.warning(f"Failed to send invitation email for {role.value}: {str(e)}")
    
    return InviteManagedUserResponse(
        message=f"{role.value.replace('_', ' ').title()} invited successfully",
        reset_link=reset_link,
    )


def update_user_by_role(
    user_id: str,
    payload: UpdateManagedUserRequest,
    role: UserRole,
    db: Session,
    building_id: uuid.UUID | None = None,
) -> ManagedUserResponse:
    try:
        parsed_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id") from exc

    if role == UserRole.RESIDENT:
        profile_query = db.query(ResidentProfile).join(User, User.id == ResidentProfile.user_id).filter(
            ResidentProfile.user_id == parsed_id
        )
        if building_id is not None:
            profile_query = profile_query.join(Unit, Unit.id == ResidentProfile.unit_id).filter(
                Unit.building_id == building_id
            )
        profile = profile_query.first()
        user = profile.user if profile else None
    elif role == UserRole.SECURITY:
        profile_query = db.query(SecurityProfile).join(User, User.id == SecurityProfile.user_id).filter(
            SecurityProfile.user_id == parsed_id
        )
        if building_id is not None:
            profile_query = profile_query.filter(SecurityProfile.assigned_building_id == building_id)
        profile = profile_query.first()
        user = profile.user if profile else None
    else:
        user = db.query(User).filter(User.id == parsed_id, User.role == role).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_email_owner = (
        db.query(User)
        .filter(User.email == payload.email, User.id != parsed_id)
        .first()
    )
    if existing_email_owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user.full_name = payload.full_name
    user.email = payload.email
    user.phone_number = payload.phone_number
    user.profile_image = payload.profile_image
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    return _serialize_user(user)


def delete_user_by_role(user_id: str, role: UserRole, db: Session, building_id: uuid.UUID | None = None) -> dict:
    try:
        parsed_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id") from exc

    if role == UserRole.RESIDENT:
        profile_query = db.query(ResidentProfile).join(User, User.id == ResidentProfile.user_id).filter(
            ResidentProfile.user_id == parsed_id
        )
        if building_id is not None:
            profile_query = profile_query.join(Unit, Unit.id == ResidentProfile.unit_id).filter(
                Unit.building_id == building_id
            )
        profile = profile_query.first()
        user = profile.user if profile else None
    elif role == UserRole.SECURITY:
        profile_query = db.query(SecurityProfile).join(User, User.id == SecurityProfile.user_id).filter(
            SecurityProfile.user_id == parsed_id
        )
        if building_id is not None:
            profile_query = profile_query.filter(SecurityProfile.assigned_building_id == building_id)
        profile = profile_query.first()
        user = profile.user if profile else None
    else:
        user = db.query(User).filter(User.id == parsed_id, User.role == role).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if role == UserRole.RESIDENT:
        resident_profile = db.query(ResidentProfile).filter(ResidentProfile.user_id == user.id).first()
        if resident_profile and resident_profile.unit_id is not None:
            unit = db.query(Unit).filter(Unit.id == resident_profile.unit_id).first()
            if unit:
                unit.status = UnitStatus.VACANT

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


def _normalize_unit_location(building_type: BuildingType, floor: int | None, plot_number: str | None) -> tuple[int | None, str | None]:
    if building_type == BuildingType.APARTMENT_TOWER:
        if floor is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="floor is required for apartment towers")
        return floor, None

    if floor is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="floor must be null for this building type")
    if not plot_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="plot_number is required for this building type")
    return None, plot_number


def _serialize_announcement(announcement: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse.model_validate(announcement)


def _serialize_event(event: Event) -> EventResponse:
    return EventResponse.model_validate(event)


def _serialize_maintenance_request(record: MaintenanceRequest) -> MaintenanceRequestResponse:
    response = MaintenanceRequestResponse.model_validate(record)
    response.resident_name = record.resident.full_name if record.resident is not None else None
    response.unit_number = record.unit.unit_number if record.unit is not None else None
    return response


def get_announcements(db: Session, building_id: uuid.UUID) -> list[AnnouncementResponse]:
    announcements = (
        db.query(Announcement)
        .filter(Announcement.building_id == building_id)
        .order_by(Announcement.published_at.desc(), Announcement.created_at.desc())
        .all()
    )
    return [_serialize_announcement(announcement) for announcement in announcements]


def create_announcement(
    db: Session,
    building_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AnnouncementCreateRequest,
) -> AnnouncementResponse:
    announcement = Announcement(
        title=data.title,
        content=data.content,
        priority=data.priority,
        author_user_id=user_id,
        building_id=building_id,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return _serialize_announcement(announcement)


def delete_announcement(db: Session, building_id: uuid.UUID, announcement_id: uuid.UUID) -> dict:
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    if announcement.building_id != building_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Announcement does not belong to your building")

    db.delete(announcement)
    db.commit()
    return {"message": "Announcement deleted"}


def get_maintenance_requests(
    db: Session,
    building_id: uuid.UUID,
    status_filter: MaintenanceStatus | None = None,
) -> list[MaintenanceRequestResponse]:
    query = (
        db.query(MaintenanceRequest)
        .join(Unit, Unit.id == MaintenanceRequest.unit_id)
        .filter(Unit.building_id == building_id)
        .options(joinedload(MaintenanceRequest.unit), joinedload(MaintenanceRequest.resident))
        .order_by(MaintenanceRequest.created_at.desc())
    )
    if status_filter is not None:
        query = query.filter(MaintenanceRequest.status == status_filter)
    records = query.all()
    return [_serialize_maintenance_request(record) for record in records]


def update_maintenance_status(
    db: Session,
    request_id: uuid.UUID,
    building_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    data: MaintenanceStatusUpdateRequest,
) -> MaintenanceRequestResponse:
    record = db.query(MaintenanceRequest).options(joinedload(MaintenanceRequest.unit)).filter(
        MaintenanceRequest.id == request_id
    ).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
    if record.unit is None or record.unit.building_id != building_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request does not belong to your building")

    new_status = data.status
    current_status = record.status

    if new_status == MaintenanceStatus.IN_PROGRESS:
        if current_status != MaintenanceStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request must be open to start work")
    elif new_status == MaintenanceStatus.RESOLVED:
        if current_status != MaintenanceStatus.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request must be in progress to resolve")
        if not data.resolution_note or not data.resolution_note.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolution note is required")
        record.resolved_at = datetime.utcnow()
        record.resolution_note = data.resolution_note.strip()
    elif new_status == MaintenanceStatus.CANCELLED:
        if current_status == MaintenanceStatus.RESOLVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolved requests cannot be cancelled")
        if current_status not in {MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request cannot be cancelled")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported maintenance status")

    record.status = new_status
    if data.resolution_note is not None and new_status != MaintenanceStatus.RESOLVED:
        record.resolution_note = data.resolution_note.strip() or None
    record.updated_by = admin_user_id
    db.commit()
    db.refresh(record)
    return _serialize_maintenance_request(record)


def get_events(db: Session, building_id: uuid.UUID) -> list[EventResponse]:
    events = (
        db.query(Event)
        .filter(Event.building_id == building_id, Event.is_active.is_(True))
        .order_by(Event.event_date.asc(), Event.created_at.desc())
        .all()
    )
    return [_serialize_event(event) for event in events]


def create_event(
    db: Session,
    building_id: uuid.UUID,
    user_id: uuid.UUID,
    data: EventCreateRequest,
) -> EventResponse:
    event = Event(
        title=data.title,
        description=data.description,
        location=data.location,
        event_date=data.event_date,
        building_id=building_id,
        created_by=user_id,
        is_active=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize_event(event)


def delete_event(db: Session, building_id: uuid.UUID, event_id: uuid.UUID) -> dict:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.building_id != building_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Event does not belong to your building")

    event.is_active = False
    db.commit()
    return {"message": "Event deleted"}


def mark_payment_paid(
    db: Session,
    building_id: uuid.UUID,
    payment_id: str,
    notes: str | None = None,
) -> dict:
    from app.models.resident import Payment, PaymentStatus
    from app.schemas.resident import PaymentResponse
    from datetime import date

    try:
        parsed_payment_id = uuid.UUID(payment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment id") from exc

    payment = (
        db.query(Payment)
        .join(ResidentProfile, ResidentProfile.user_id == Payment.resident_id)
        .join(Unit, Unit.id == ResidentProfile.unit_id)
        .filter(Payment.id == parsed_payment_id, Unit.building_id == building_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if payment.status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This payment is already marked as paid",
        )

    if payment.status == PaymentStatus.WAIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This payment has been waived and cannot be marked as paid",
        )

    payment.status = PaymentStatus.PAID
    payment.paid_date = date.today()
    if notes:
        payment.transaction_ref = notes

    db.commit()
    db.refresh(payment)
    return PaymentResponse.model_validate(payment)


def get_payments(db: Session, building_id: uuid.UUID) -> list:
    """Get all payments for a building."""
    from app.models.resident import Payment
    from app.schemas.resident import PaymentResponse
    
    payments = (
        db.query(Payment)
        .join(ResidentProfile, ResidentProfile.user_id == Payment.resident_id)
        .join(Unit, Unit.id == ResidentProfile.unit_id)
        .filter(Unit.building_id == building_id)
        .all()
    )
    return [PaymentResponse.model_validate(p) for p in payments]


def get_residents(db: Session, building_id: uuid.UUID) -> list:
    """Get all residents for a building."""
    residents = (
        db.query(ResidentProfile, Unit)
        .join(Unit, Unit.id == ResidentProfile.unit_id)
        .join(User, User.id == ResidentProfile.user_id)
        .filter(Unit.building_id == building_id)
        .all()
    )
    
    result = []
    for resident_profile, unit in residents:
        result.append({
            "id": str(resident_profile.user_id),
            "full_name": resident_profile.full_name or "",
            "unit_number": unit.unit_number or None,
        })
    return result


def raise_bulk_due(
    db: Session,
    building_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    payment_type: str,
    amount: float,
    due_date: str,
    description: str | None = None,
) -> dict:
    """Raise a due for all residents in the building."""
    from app.models.resident import Payment, PaymentStatus, PaymentType
    from datetime import date
    
    # Validate payment type
    try:
        payment_type_enum = PaymentType(payment_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment type") from exc
    
    # Parse due date
    try:
        due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from exc
    
    # Get all residents in the building
    residents = (
        db.query(ResidentProfile, Unit)
        .join(Unit, Unit.id == ResidentProfile.unit_id)
        .filter(Unit.building_id == building_id)
        .all()
    )
    
    if not residents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No residents found in this building")
    
    created_count = 0
    for resident_profile, _ in residents:
        payment = Payment(
            id=uuid.uuid4(),
            resident_id=resident_profile.user_id,
            amount=amount,
            type=payment_type_enum,
            status=PaymentStatus.PENDING,
            due_date=due_date_obj,
            description=description,
            created_by=admin_user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(payment)
        created_count += 1
    
    db.commit()
    return {"message": f"Due raised for {created_count} residents"}


def raise_individual_due(
    db: Session,
    building_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    resident_id: str,
    payment_type: str,
    amount: float,
    due_date: str,
    description: str | None = None,
) -> dict:
    """Raise a due for a specific resident."""
    from app.models.resident import Payment, PaymentStatus, PaymentType
    from datetime import date
    
    # Validate payment type
    try:
        payment_type_enum = PaymentType(payment_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment type") from exc
    
    # Parse due date
    try:
        due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD") from exc
    
    # Verify resident exists in this building
    try:
        resident_uuid = uuid.UUID(resident_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resident id") from exc
    
    resident = (
        db.query(ResidentProfile)
        .join(Unit, Unit.id == ResidentProfile.unit_id)
        .filter(ResidentProfile.user_id == resident_uuid, Unit.building_id == building_id)
        .first()
    )
    
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found in this building")
    
    # Create payment
    payment = Payment(
        id=uuid.uuid4(),
        resident_id=resident_uuid,
        amount=amount,
        type=payment_type_enum,
        status=PaymentStatus.PENDING,
        due_date=due_date_obj,
        description=description,
        created_by=admin_user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    from app.schemas.resident import PaymentResponse
    return PaymentResponse.model_validate(payment)


def waive_payment(
    db: Session,
    building_id: uuid.UUID,
    payment_id: str,
) -> dict:
    """Waive a payment."""
    from app.models.resident import Payment, PaymentStatus
    from app.schemas.resident import PaymentResponse
    
    try:
        parsed_payment_id = uuid.UUID(payment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment id") from exc
    
    payment = (
        db.query(Payment)
        .join(ResidentProfile, ResidentProfile.user_id == Payment.resident_id)
        .join(Unit, Unit.id == ResidentProfile.unit_id)
        .filter(Payment.id == parsed_payment_id, Unit.building_id == building_id)
        .first()
    )
    
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    if payment.status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot waive a payment that is already paid",
        )
    
    payment.status = PaymentStatus.WAIVED
    db.commit()
    db.refresh(payment)
    return PaymentResponse.model_validate(payment)