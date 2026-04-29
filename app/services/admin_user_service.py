import uuid
from datetime import datetime, timedelta, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.resident import ResidentProfile, SecurityProfile, Unit
from app.models.user import User, UserRole
from app.schemas.admin_management import (
    AdminDashboardStatsResponse,
    CreateManagedUserRequest,
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
    resident_query = db.query(func.count(User.id)).filter(User.role == UserRole.RESIDENT)
    security_query = db.query(func.count(User.id)).filter(User.role == UserRole.SECURITY)
    resident_recent_query = db.query(func.count(User.id)).filter(
        User.role == UserRole.RESIDENT,
        User.created_at >= since,
    )
    security_recent_query = db.query(func.count(User.id)).filter(
        User.role == UserRole.SECURITY,
        User.created_at >= since,
    )

    if building_id is not None:
        resident_query = resident_query.join(ResidentProfile, ResidentProfile.user_id == User.id).join(
            Unit, Unit.id == ResidentProfile.unit_id
        ).filter(Unit.building_id == building_id)
        security_query = security_query.join(SecurityProfile, SecurityProfile.user_id == User.id).filter(
            SecurityProfile.assigned_building_id == building_id
        )
        resident_recent_query = resident_recent_query.join(ResidentProfile, ResidentProfile.user_id == User.id).join(
            Unit, Unit.id == ResidentProfile.unit_id
        ).filter(Unit.building_id == building_id)
        security_recent_query = security_recent_query.join(SecurityProfile, SecurityProfile.user_id == User.id).filter(
            SecurityProfile.assigned_building_id == building_id
        )

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


def list_users_by_role(role: UserRole, db: Session, building_id: uuid.UUID | None = None) -> list[ManagedUserResponse]:
    query = db.query(User).filter(User.role == role)
    if building_id is not None:
        if role == UserRole.RESIDENT:
            query = query.join(ResidentProfile, ResidentProfile.user_id == User.id).join(
                Unit, Unit.id == ResidentProfile.unit_id
            ).filter(Unit.building_id == building_id)
        elif role == UserRole.SECURITY:
            query = query.join(SecurityProfile, SecurityProfile.user_id == User.id).filter(
                SecurityProfile.assigned_building_id == building_id
            )
    users = query.order_by(User.created_at.desc()).all()
    return [_serialize_user(user) for user in users]


def create_user_by_role(
    payload: CreateManagedUserRequest,
    role: UserRole,
    db: Session,
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
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


def invite_user_by_role(
    payload: InviteManagedUserRequest,
    role: UserRole,
    db: Session,
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

    user_query = db.query(User).filter(User.id == parsed_id, User.role == role)
    if building_id is not None:
        if role == UserRole.RESIDENT:
            user_query = user_query.join(ResidentProfile, ResidentProfile.user_id == User.id).join(
                Unit, Unit.id == ResidentProfile.unit_id
            ).filter(Unit.building_id == building_id)
        elif role == UserRole.SECURITY:
            user_query = user_query.join(SecurityProfile, SecurityProfile.user_id == User.id).filter(
                SecurityProfile.assigned_building_id == building_id
            )
    user = user_query.first()
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

    user_query = db.query(User).filter(User.id == parsed_id, User.role == role)
    if building_id is not None:
        if role == UserRole.RESIDENT:
            user_query = user_query.join(ResidentProfile, ResidentProfile.user_id == User.id).join(
                Unit, Unit.id == ResidentProfile.unit_id
            ).filter(Unit.building_id == building_id)
        elif role == UserRole.SECURITY:
            user_query = user_query.join(SecurityProfile, SecurityProfile.user_id == User.id).filter(
                SecurityProfile.assigned_building_id == building_id
            )
    user = user_query.first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}