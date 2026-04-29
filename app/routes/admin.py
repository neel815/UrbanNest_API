from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import AdminProfile
from app.models.user import User, UserRole
from app.schemas.admin_management import (
    AdminDashboardStatsResponse,
    CreateManagedUserRequest,
    InviteManagedUserRequest,
    InviteManagedUserResponse,
    ManagedUserResponse,
    UpdateManagedUserRequest,
)
from app.services.admin_user_service import (
    create_user_by_role,
    delete_user_by_role,
    get_admin_dashboard_stats,
    invite_user_by_role,
    list_users_by_role,
    require_admin,
    update_user_by_role,
)
from app.services.auth_service import get_current_user

router = APIRouter()


def _get_admin_building_id(current_user: User, db: Session):
    admin_profile = db.query(AdminProfile).filter(AdminProfile.user_id == current_user.id).first()
    if not admin_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin profile not found")
    if admin_profile.building_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin building not assigned")
    return admin_profile.building_id


@router.get("/dashboard/stats", response_model=AdminDashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminDashboardStatsResponse:
    require_admin(current_user)
    building_id = _get_admin_building_id(current_user, db)
    return get_admin_dashboard_stats(db, building_id)


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
    return create_user_by_role(payload, UserRole.RESIDENT, db)


@router.post("/residents/invite", response_model=InviteManagedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_resident(
    payload: InviteManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteManagedUserResponse:
    require_admin(current_user)
    return invite_user_by_role(payload, UserRole.RESIDENT, db)


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
    return create_user_by_role(payload, UserRole.SECURITY, db)


@router.post("/security/invite", response_model=InviteManagedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_security(
    payload: InviteManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteManagedUserResponse:
    require_admin(current_user)
    return invite_user_by_role(payload, UserRole.SECURITY, db)


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