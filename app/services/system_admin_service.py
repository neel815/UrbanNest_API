import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminInviteRequest,
    AdminInviteResponse,
    DashboardStatsResponse,
    SettingsUpdateRequest,
    UserSummary,
)
from app.utils.security import hash_password

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


def list_admins(db: Session) -> list[UserSummary]:
    admins = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.created_at.desc()).all()
    return [
        UserSummary(
            id=str(admin.id),
            full_name=admin.full_name,
            email=admin.email,
            role=admin.role.value,
            created_at=admin.created_at.isoformat(),
            must_reset_password=admin.must_reset_password,
            profile_image=admin.profile_image,
        )
        for admin in admins
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

    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    return AdminInviteResponse(message="Admin created and reset link generated", reset_link=reset_link)


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