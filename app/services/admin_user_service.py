import uuid
from datetime import datetime, timedelta, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.resident import Building, BuildingType, ResidentProfile, SecurityProfile, Unit, UnitStatus
from app.models.user import User, UserRole
from app.schemas.admin_management import (
    AdminBuildingInfoResponse,
    AdminDashboardStatsResponse,
    CreateManagedUserRequest,
    UnitCreateRequest,
    UnitResponse,
    UnitUpdateRequest,
    InviteManagedUserRequest,
    InviteManagedUserResponse,
    ManagedUserResponse,
    UpdateManagedUserRequest,
)
from app.utils.security import hash_password


def require_admin(current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


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


def _serialize_user(user: User) -> ManagedUserResponse:
    return ManagedUserResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        profile_image=user.profile_image,
        created_at=user.created_at.isoformat(),
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
        return [_serialize_user(profile.user) for profile in profiles]

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