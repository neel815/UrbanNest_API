from fastapi import APIRouter, Depends, HTTPException, status
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
from app.services.system_admin_service import (
    get_dashboard_stats,
    get_settings_me as get_settings_me_service,
    invite_admin as invite_admin_service,
    list_admins as list_admins_service,
    require_system_admin,
    update_settings_me as update_settings_me_service,
)

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    require_system_admin(current_user)
    return get_dashboard_stats(db)


@router.get("/admins", response_model=list[UserSummary])
def list_admins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserSummary]:
    require_system_admin(current_user)
    return list_admins_service(db)


@router.post("/admins/invite", response_model=AdminInviteResponse, status_code=status.HTTP_201_CREATED)
def invite_admin(
    payload: AdminInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminInviteResponse:
    require_system_admin(current_user)
    return invite_admin_service(payload, db)


@router.get("/settings/me")
def get_settings_me(current_user: User = Depends(get_current_user)) -> dict:
    require_system_admin(current_user)
    return get_settings_me_service(current_user)


@router.put("/settings/me")
def update_settings_me(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_system_admin(current_user)
    return update_settings_me_service(payload, current_user, db)
