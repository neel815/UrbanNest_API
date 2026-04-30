from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import AdminProfile
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
from app.services.admin_user_service import (
    create_user_by_role,
    create_unit_for_building,
    delete_user_by_role,
    delete_unit_for_building,
    get_admin_dashboard_stats,
    get_admin_building_info,
    invite_user_by_role,
    list_users_by_role,
    list_units_for_building,
    require_admin,
    update_user_by_role,
    update_unit_for_building,
)
from app.services.auth_service import get_current_user

router = APIRouter()


def _get_admin_building_id(current_user: User, db: Session):
    admin_profile = db.query(AdminProfile).filter(AdminProfile.user_id == current_user.id).first()
    if not admin_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin not assigned to any building")
    if admin_profile.building_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin not assigned to any building")
    return admin_profile.building_id


@router.get("/dashboard/stats", response_model=AdminDashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminDashboardStatsResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return get_admin_dashboard_stats(db, building_id)


@router.get("/building-info", response_model=AdminBuildingInfoResponse)
def building_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminBuildingInfoResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return get_admin_building_info(db, building_id)


@router.get("/residents", response_model=list[ManagedUserResponse])
def list_residents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ManagedUserResponse]:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return list_users_by_role(UserRole.RESIDENT, db, building_id)


@router.post("/residents", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
def create_resident(
    payload: CreateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return create_user_by_role(payload, UserRole.RESIDENT, db, building_id)


@router.post("/residents/invite", response_model=InviteManagedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_resident(
    payload: InviteManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteManagedUserResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return invite_user_by_role(payload, UserRole.RESIDENT, db, building_id)


@router.get("/units", response_model=list[UnitResponse])
def list_units(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UnitResponse]:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return list_units_for_building(db, building_id)


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return create_unit_for_building(db, building_id, payload)


@router.patch("/units/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: str,
    payload: UnitUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return update_unit_for_building(db, building_id, unit_id, payload)


@router.delete("/units/{unit_id}")
def delete_unit(
    unit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return delete_unit_for_building(db, building_id, unit_id)


@router.put("/residents/{user_id}", response_model=ManagedUserResponse)
def update_resident(
    user_id: str,
    payload: UpdateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return update_user_by_role(user_id, payload, UserRole.RESIDENT, db, building_id)


@router.delete("/residents/{user_id}")
def delete_resident(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return delete_user_by_role(user_id, UserRole.RESIDENT, db, building_id)


@router.get("/security", response_model=list[ManagedUserResponse])
def list_security(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ManagedUserResponse]:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return list_users_by_role(UserRole.SECURITY, db, building_id)


@router.post("/security", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
def create_security(
    payload: CreateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return create_user_by_role(payload, UserRole.SECURITY, db, building_id)


@router.post("/security/invite", response_model=InviteManagedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_security(
    payload: InviteManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteManagedUserResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return invite_user_by_role(payload, UserRole.SECURITY, db, building_id)


@router.put("/security/{user_id}", response_model=ManagedUserResponse)
def update_security(
    user_id: str,
    payload: UpdateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return update_user_by_role(user_id, payload, UserRole.SECURITY, db, building_id)


@router.delete("/security/{user_id}")
def delete_security(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return delete_user_by_role(user_id, UserRole.SECURITY, db, building_id)