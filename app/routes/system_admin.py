from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.routes.auth import get_current_user
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
from app.services.system_admin_service import (
    create_building,
    get_dashboard_stats,
    get_platform_activity,
    get_top_societies,
    get_settings_me as get_settings_me_service,
    invite_admin as invite_admin_service,
    delete_admin as delete_admin_service,
    list_admins as list_admins_service,
    list_buildings,
    require_system_admin,
    delete_building,
    update_settings_me as update_settings_me_service,
    update_building,
)

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    require_system_admin(current_user)
    return get_dashboard_stats(db)


@router.get("/dashboard/activity", response_model=list[PlatformActivityItem])
def platform_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlatformActivityItem]:
    require_system_admin(current_user)
    return get_platform_activity(db)


@router.get("/dashboard/top-societies", response_model=list[TopSocietyItem])
def top_societies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TopSocietyItem]:
    require_system_admin(current_user)
    return get_top_societies(db)


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


@router.delete("/admins/{admin_id}")
def delete_admin(
    admin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_system_admin(current_user)
    return delete_admin_service(admin_id, db)


@router.post("/buildings", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
def create_building_endpoint(
    payload: BuildingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BuildingResponse:
    require_system_admin(current_user)
    return create_building(payload, db)


@router.get("/buildings", response_model=list[BuildingResponse])
def list_buildings_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BuildingResponse]:
    require_system_admin(current_user)
    return list_buildings(db)


@router.patch("/buildings/{building_id}", response_model=BuildingResponse)
def update_building_endpoint(
    building_id: str,
    payload: BuildingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BuildingResponse:
    require_system_admin(current_user)
    return update_building(building_id, payload, db)


@router.delete("/buildings/{building_id}")
def delete_building_endpoint(
    building_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_system_admin(current_user)
    return delete_building(building_id, db)


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
