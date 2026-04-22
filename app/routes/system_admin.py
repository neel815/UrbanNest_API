import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.routes.auth import get_current_user
from app.schemas.admin import (
    AdminInviteRequest,
    AdminInviteResponse,
    DashboardStatsResponse,
    SettingsUpdateRequest,
    UserSummary,
)
from app.utils.security import hash_password

router = APIRouter()

APP_SETTINGS = {"app_name": "UrbanNest"}


def _require_system_admin(current_user: User) -> None:
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System Admin only")


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    _require_system_admin(current_user)
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


@router.get("/admins", response_model=list[UserSummary])
def list_admins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserSummary]:
    _require_system_admin(current_user)
    admins = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.created_at.desc()).all()
    return [
        UserSummary(
            id=str(a.id),
            full_name=a.full_name,
            email=a.email,
            role=a.role.value,
            created_at=a.created_at.isoformat(),
            must_reset_password=a.must_reset_password,
            profile_image_url=a.profile_image_url,
        )
        for a in admins
    ]


@router.post("/admins/invite", response_model=AdminInviteResponse, status_code=status.HTTP_201_CREATED)
def invite_admin(
    payload: AdminInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminInviteResponse:
    _require_system_admin(current_user)
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
    # In production, send this link by email provider (SMTP/SES/etc).
    return AdminInviteResponse(message="Admin created and reset link generated", reset_link=reset_link)


@router.get("/settings/me")
def get_settings_me(current_user: User = Depends(get_current_user)) -> dict:
    _require_system_admin(current_user)
    return {
        "app_name": APP_SETTINGS["app_name"],
        "full_name": current_user.full_name,
        "email": current_user.email,
        "profile_image_url": current_user.profile_image_url,
    }


@router.put("/settings/me")
def update_settings_me(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_system_admin(current_user)
    APP_SETTINGS["app_name"] = payload.app_name
    current_user.full_name = payload.full_name
    current_user.profile_image_url = payload.profile_image_url
    db.commit()
    return {
        "message": "Settings updated",
        "app_name": APP_SETTINGS["app_name"],
        "full_name": current_user.full_name,
        "profile_image_url": current_user.profile_image_url,
    }
