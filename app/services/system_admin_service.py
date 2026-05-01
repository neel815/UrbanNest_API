import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.admin import Building, Unit
from app.models.resident import ResidentProfile
from app.models.user import User, UserRole
from app.models.admin import AdminProfile
from app.schemas.system_admin import (
    AdminInviteRequest,
    AdminInviteResponse,
    BuildingCreateRequest,
    BuildingResponse,
    BuildingUpdateRequest,
    DashboardStatsResponse,
    PlatformActivityItem,
    SettingsUpdateRequest,
    TopSocietyItem,
    UserSummary,
)
from app.utils.security import hash_password

import uuid
APP_SETTINGS = {"app_name": "UrbanNest"}


def require_system_admin(current_user: User) -> None:
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System Admin only")


def get_dashboard_stats(db: Session) -> DashboardStatsResponse:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    return DashboardStatsResponse(
        total_users=db.query(func.count(User.id)).scalar() or 0,
        total_admins=db.query(func.count(User.id)).filter(User.role == UserRole.ADMIN).scalar() or 0,
        total_residents=db.query(func.count(User.id)).filter(User.role == UserRole.RESIDENT).scalar() or 0,
        total_security=db.query(func.count(User.id)).filter(User.role == UserRole.SECURITY).scalar() or 0,
        residents_joined_last_30_days=(
            db.query(func.count(User.id))
            .filter(User.role == UserRole.RESIDENT, User.created_at >= since)
            .scalar()
            or 0
        ),
    )


def _relative_time(value: datetime) -> str:
    delta = datetime.now(timezone.utc) - value
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return f'{seconds // 60}m ago'
    if seconds < 86400:
        return f'{seconds // 3600}h ago'
    return f'{seconds // 86400}d ago'


def _initials(name: str) -> str:
    parts = [part for part in name.split(' ') if part]
    return ''.join(part[0].upper() for part in parts[:2])


def get_platform_activity(db: Session) -> list[PlatformActivityItem]:
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(3).all()
    items: list[PlatformActivityItem] = []

    for user in recent_users:
        if user.role == UserRole.ADMIN:
            title = (
                f'{user.full_name} invited a new admin'
                if user.must_reset_password
                else f'{user.full_name} activated admin access'
            )
            level = 'info' if user.must_reset_password else 'success'
        elif user.role == UserRole.SECURITY:
            title = f'{user.full_name} added a security guard'
            level = 'warning'
        elif user.role == UserRole.RESIDENT:
            title = f'{user.full_name} joined as a resident'
            level = 'success'
        else:
            title = f'{user.full_name} updated system settings'
            level = 'info'

        items.append(
            PlatformActivityItem(
                initials=_initials(user.full_name),
                title=title,
                timestamp=_relative_time(user.created_at),
                level=level,
            )
        )

    if items:
        return items

    return [PlatformActivityItem(initials='RM', title='No recent activity yet', timestamp='just now', level='info')]


def get_top_societies(db: Session) -> list[TopSocietyItem]:
    rows = (
        db.query(
            Building.name.label('name'),
            func.count(distinct(Unit.id)).label('unit_count'),
            func.count(distinct(ResidentProfile.id)).label('resident_count'),
        )
        .outerjoin(Unit, Unit.building_id == Building.id)
        .outerjoin(ResidentProfile, ResidentProfile.unit_id == Unit.id)
        .group_by(Building.id)
        .order_by(
            func.count(distinct(ResidentProfile.id)).desc(),
            func.count(distinct(Unit.id)).desc(),
            Building.name.asc(),
        )
        .limit(3)
        .all()
    )

    items: list[TopSocietyItem] = []
    for row in rows:
        units = int(row.unit_count or 0)
        residents = int(row.resident_count or 0)
        occupancy_percent = int(round((residents / units) * 100)) if units else 0
        items.append(
            TopSocietyItem(
                name=row.name,
                units=units,
                occupancy_percent=occupancy_percent,
            )
        )

    if items:
        return items

    return [
        TopSocietyItem(name='Skyline Towers', units=420, occupancy_percent=92),
        TopSocietyItem(name='Palm Grove', units=286, occupancy_percent=81),
        TopSocietyItem(name='Lotus Residency', units=198, occupancy_percent=74),
    ]


def list_admins(db: Session) -> list[UserSummary]:
    admins = (
        db.query(User, AdminProfile, Building)
        .outerjoin(AdminProfile, AdminProfile.user_id == User.id)
        .outerjoin(Building, Building.id == AdminProfile.building_id)
        .filter(User.role == UserRole.ADMIN)
        .order_by(User.created_at.desc())
        .all()
    )
    return [
        UserSummary(
            id=str(admin.id),
            full_name=admin.full_name,
            email=admin.email,
            role=admin.role.value,
            created_at=admin.created_at.isoformat(),
            must_reset_password=admin.must_reset_password,
            building_id=str(admin_profile.building_id) if admin_profile and admin_profile.building_id else None,
            building_name=building.name if building else None,
            profile_image=admin.profile_image,
        )
        for admin, admin_profile, building in admins
    ]


def invite_admin(payload: AdminInviteRequest, db: Session) -> AdminInviteResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    reset_token = secrets.token_urlsafe(32)
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(secrets.token_urlsafe(20)),
        role=UserRole.ADMIN,
        must_reset_password=True,
        reset_token=reset_token,
        reset_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create admin_profile with building assignment
    admin_profile = AdminProfile(
        user_id=user.id,
        building_id=payload.building_id,
    )
    db.add(admin_profile)
    db.commit()

    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    return AdminInviteResponse(message="Admin created and reset link generated", reset_link=reset_link)


def delete_admin(admin_id: str, db: Session) -> dict:
    try:
        parsed_id = uuid.UUID(admin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid admin id") from exc

    admin = (
        db.query(User)
        .join(AdminProfile, AdminProfile.user_id == User.id)
        .filter(User.id == parsed_id, User.role == UserRole.ADMIN)
        .first()
    )
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    db.delete(admin)
    db.commit()
    return {"message": "Admin deleted"}


def get_settings_me(current_user: User) -> dict:
    return {
        "app_name": APP_SETTINGS["app_name"],
        "full_name": current_user.full_name,
        "email": current_user.email,
        "profile_image": current_user.profile_image,
    }


def update_settings_me(
    payload: SettingsUpdateRequest,
    current_user: User,
    db: Session,
) -> dict:
    APP_SETTINGS["app_name"] = payload.app_name
    current_user.full_name = payload.full_name
    current_user.profile_image = payload.profile_image
    db.commit()
    return {
        "message": "Settings updated",
        "app_name": APP_SETTINGS["app_name"],
        "full_name": current_user.full_name,
        "profile_image": current_user.profile_image,
    }

def create_building(payload: BuildingCreateRequest, db: Session) -> BuildingResponse:
    """Create a new building"""
    if db.query(Building).filter(Building.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Building name already exists")

    building = Building(
        name=payload.name,
        address=payload.address,
        description=payload.description,
        building_type=payload.building_type,
        status=payload.status,
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return BuildingResponse.model_validate(building)


def list_buildings(db: Session) -> list[BuildingResponse]:
    """List all buildings"""
    buildings = db.query(Building).order_by(Building.created_at.desc()).all()
    return [BuildingResponse.model_validate(building) for building in buildings]


def get_building(building_id: str, db: Session) -> BuildingResponse:
    """Get a specific building by ID"""
    try:
        parsed_id = uuid.UUID(building_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid building id") from exc

    building = db.query(Building).filter(Building.id == parsed_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    return BuildingResponse.model_validate(building)


def update_building(building_id: str, payload: BuildingUpdateRequest, db: Session) -> BuildingResponse:
    """Update a building"""
    try:
        parsed_id = uuid.UUID(building_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid building id") from exc

    building = db.query(Building).filter(Building.id == parsed_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    if payload.name and payload.name != building.name:
        if db.query(Building).filter(Building.name == payload.name).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Building name already exists")
        building.name = payload.name

    if payload.address:
        building.address = payload.address
    if payload.description is not None:
        building.description = payload.description
    if payload.building_type is not None:
        building.building_type = payload.building_type
    if payload.status:
        building.status = payload.status

    db.commit()
    db.refresh(building)
    return BuildingResponse.model_validate(building)


def delete_building(building_id: str, db: Session) -> dict:
    """Delete a building"""
    try:
        parsed_id = uuid.UUID(building_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid building id") from exc

    building = db.query(Building).filter(Building.id == parsed_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    has_admins = db.query(AdminProfile).filter(AdminProfile.building_id == parsed_id).first()
    if has_admins:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Building has assigned admins")

    db.delete(building)
    db.commit()
    return {"message": "Building deleted successfully"}
