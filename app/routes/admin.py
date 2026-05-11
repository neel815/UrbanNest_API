from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.admin import (
    AnnouncementCreateRequest,
    AnnouncementResponse,
    AdminBuildingInfoResponse,
    AdminDashboardStatsResponse,
    PatrolRouteCreateRequest,
    PatrolRouteResponse,
    EventCreateRequest,
    EventResponse,
    CreateManagedUserRequest,
    MaintenanceResolveRequest,
    MaintenanceStatusUpdateRequest,
    MarkPaymentPaidRequest,
    RaiseBulkDueRequest,
    RaiseIndividualDueRequest,
    ResidentListResponse,
    UnitCreateRequest,
    UnitResponse,
    UnitUpdateRequest,
    InviteManagedUserRequest,
    InviteManagedUserResponse,
    ManagedUserResponse,
    AdminResidentDetailResponse,
    UpdateManagedUserRequest,
    SecurityOverviewResponse,
)
from app.services.admin_user_service import (
    create_announcement,
    create_event,
    create_user_by_role,
    create_unit_for_building,
    delete_announcement,
    delete_event,
    delete_user_by_role,
    delete_unit_for_building,
    get_admin_dashboard_stats,
    get_admin_building_info,
    get_admin_building_id,
    get_announcements,
    get_maintenance_requests,
    get_events,
    get_payments,
    get_residents,
    get_resident_detail,
    invite_user_by_role,
    list_users_by_role,
    list_units_for_building,
    get_security_overview,
    mark_payment_paid,
    raise_bulk_due,
    raise_individual_due,
    waive_payment,
    require_admin,
    update_maintenance_status,
    update_user_by_role,
    update_unit_for_building,
    create_patrol_route,
    delete_patrol_route,
    get_patrol_routes,
)
from app.services.scheduler_service import mark_overdue_payments
from app.services.auth_service import get_current_user
from app.models.resident import MaintenanceStatus
from app.schemas.resident import MaintenanceRequestResponse

router = APIRouter()


@router.get("/dashboard/stats", response_model=AdminDashboardStatsResponse)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminDashboardStatsResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_admin_dashboard_stats(db, building_id)


@router.get("/building-info", response_model=AdminBuildingInfoResponse)
def building_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminBuildingInfoResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_admin_building_info(db, building_id)


@router.get("/announcements", response_model=list[AnnouncementResponse])
def list_announcements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnnouncementResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_announcements(db, building_id)


@router.post("/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_admin_announcement(
    payload: AnnouncementCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnnouncementResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return create_announcement(db, building_id, current_user.id, payload)


@router.delete("/announcements/{announcement_id}")
def remove_admin_announcement(
    announcement_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return delete_announcement(db, building_id, announcement_id)


@router.get("/maintenance", response_model=list[MaintenanceRequestResponse])
def list_maintenance_requests(
    status: MaintenanceStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceRequestResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_maintenance_requests(db, building_id, status)


@router.patch("/maintenance/{request_id}/start", response_model=MaintenanceRequestResponse)
def start_maintenance_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRequestResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return update_maintenance_status(
        db,
        request_id,
        building_id,
        current_user.id,
        MaintenanceStatusUpdateRequest(status=MaintenanceStatus.IN_PROGRESS),
    )


@router.patch("/maintenance/{request_id}/resolve", response_model=MaintenanceRequestResponse)
def resolve_maintenance_request(
    request_id: UUID,
    payload: MaintenanceResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRequestResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return update_maintenance_status(
        db,
        request_id,
        building_id,
        current_user.id,
        MaintenanceStatusUpdateRequest(status=MaintenanceStatus.RESOLVED, resolution_note=payload.resolution_note),
    )


@router.patch("/maintenance/{request_id}/cancel", response_model=MaintenanceRequestResponse)
def cancel_maintenance_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRequestResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return update_maintenance_status(
        db,
        request_id,
        building_id,
        current_user.id,
        MaintenanceStatusUpdateRequest(status=MaintenanceStatus.CANCELLED),
    )


@router.get("/events", response_model=list[EventResponse])
def list_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EventResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_events(db, building_id)


@router.get("/patrol-routes", response_model=list[PatrolRouteResponse])
def list_patrol_routes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PatrolRouteResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_patrol_routes(db, building_id)


@router.post("/patrol-routes", response_model=PatrolRouteResponse, status_code=status.HTTP_201_CREATED)
def create_admin_patrol_route(
    payload: PatrolRouteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatrolRouteResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return create_patrol_route(db, building_id, payload)


@router.delete("/patrol-routes/{route_id}")
def remove_admin_patrol_route(
    route_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return delete_patrol_route(db, building_id, str(route_id))


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_admin_event(
    payload: EventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return create_event(db, building_id, current_user.id, payload)


@router.delete("/events/{event_id}")
def remove_admin_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return delete_event(db, building_id, event_id)


@router.get("/residents", response_model=list[ManagedUserResponse])
def list_residents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ManagedUserResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return list_users_by_role(UserRole.RESIDENT, db, building_id)


@router.get("/residents/detail/{resident_id}", response_model=AdminResidentDetailResponse)
def get_resident_detail_endpoint(
    resident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminResidentDetailResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_resident_detail(db, building_id, resident_id)


@router.post("/residents", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
def create_resident(
    payload: CreateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return create_user_by_role(payload, UserRole.RESIDENT, db, building_id)


@router.post("/residents/invite", response_model=InviteManagedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_resident(
    payload: InviteManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteManagedUserResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return invite_user_by_role(payload, UserRole.RESIDENT, db, building_id)


@router.get("/units", response_model=list[UnitResponse])
def list_units(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UnitResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return list_units_for_building(db, building_id)


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return create_unit_for_building(db, building_id, payload)


@router.patch("/units/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: str,
    payload: UnitUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return update_unit_for_building(db, building_id, unit_id, payload)


@router.delete("/units/{unit_id}")
def delete_unit(
    unit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return delete_unit_for_building(db, building_id, unit_id)


@router.put("/residents/{user_id}", response_model=ManagedUserResponse)
def update_resident(
    user_id: str,
    payload: UpdateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return update_user_by_role(user_id, payload, UserRole.RESIDENT, db, building_id)


@router.delete("/residents/{user_id}")
def delete_resident(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return delete_user_by_role(user_id, UserRole.RESIDENT, db, building_id)


@router.get("/security", response_model=list[ManagedUserResponse])
def list_security(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ManagedUserResponse]:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return list_users_by_role(UserRole.SECURITY, db, building_id)


@router.get("/security/stats", response_model=SecurityOverviewResponse)
def security_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> object:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_security_overview(db, building_id)


@router.post("/security", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
def create_security(
    payload: CreateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return create_user_by_role(payload, UserRole.SECURITY, db, building_id)


@router.post("/security/invite", response_model=InviteManagedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_security(
    payload: InviteManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteManagedUserResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return invite_user_by_role(payload, UserRole.SECURITY, db, building_id)


@router.put("/security/{user_id}", response_model=ManagedUserResponse)
def update_security(
    user_id: str,
    payload: UpdateManagedUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return update_user_by_role(user_id, payload, UserRole.SECURITY, db, building_id)


@router.delete("/security/{user_id}")
def delete_security(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return delete_user_by_role(user_id, UserRole.SECURITY, db, building_id)


@router.patch("/payments/{payment_id}/mark-paid", status_code=status.HTTP_200_OK)
def mark_payment_as_received(
    payment_id: str,
    payload: MarkPaymentPaidRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return mark_payment_paid(db, building_id, payment_id, payload.notes)


@router.get("/payments")
def list_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return get_payments(db, building_id)


# TESTING ONLY — Remove before production
@router.post("/payments/trigger-overdue-check")
def trigger_overdue_check(
    current_user: User = Depends(get_current_user),
) -> dict:
    require_admin(current_user)
    mark_overdue_payments()
    return {"message": "Overdue check completed"}


@router.post("/payments/bulk", status_code=status.HTTP_201_CREATED)
def raise_bulk_payment(
    payload: RaiseBulkDueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return raise_bulk_due(
        db,
        building_id,
        current_user.id,
        payload.type,
        payload.amount,
        payload.due_date,
        payload.description,
    )


@router.post("/payments/individual", status_code=status.HTTP_201_CREATED)
def raise_individual_payment(
    payload: RaiseIndividualDueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return raise_individual_due(
        db,
        building_id,
        current_user.id,
        payload.resident_id,
        payload.type,
        payload.amount,
        payload.due_date,
        payload.description,
    )


@router.patch("/payments/{payment_id}/waive", status_code=status.HTTP_200_OK)
def waive_payment_endpoint(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    building_id = get_admin_building_id(db, current_user.id)
    return waive_payment(db, building_id, payment_id)