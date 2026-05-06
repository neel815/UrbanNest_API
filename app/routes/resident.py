from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resident import (
    AnnouncementResponse,
    DashboardStats,
    EventResponse,
    ForumPostCreateRequest,
    ForumPostResponse,
    MaintenanceCreateRequest,
    MaintenanceRequestResponse,
    PaymentResponse,
    ResidentProfileResponse,
    ResidentProfileUpdateRequest,
    VisitorCreateRequest,
    VisitorResponse,
    VisitorUpdateRequest,
)
from app.services.auth_service import get_current_user
from app.services.resident_service import (
    create_forum_post,
    create_maintenance_request,
    create_visitor,
    cancel_maintenance_request,
    get_announcements,
    get_dashboard_stats,
    get_events,
    get_forum_posts,
    get_maintenance_requests,
    get_payments,
    get_resident_profile,
    get_visitors,
    pay_payment,
    require_resident,
    update_visitor_status,
    update_resident_profile,
)

router = APIRouter()


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResidentProfileResponse:
    require_resident(current_user)
    return get_resident_profile(db, current_user.id)


@router.patch("/profile")
async def update_profile(
    payload: ResidentProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResidentProfileResponse:
    require_resident(current_user)
    return update_resident_profile(db, current_user.id, payload)


@router.get("/dashboard-stats")
async def get_dashboard_stats_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    require_resident(current_user)
    return get_dashboard_stats(db, current_user.id)


@router.get("/announcements")
async def get_announcements_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnnouncementResponse]:
    require_resident(current_user)
    return get_announcements(db, current_user.id)


@router.get("/maintenance")
async def get_maintenance_requests_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceRequestResponse]:
    require_resident(current_user)
    return get_maintenance_requests(db, current_user.id)


@router.post("/maintenance")
async def create_maintenance_request_endpoint(
    request: MaintenanceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRequestResponse:
    require_resident(current_user)
    return create_maintenance_request(db, current_user.id, request)


@router.patch("/maintenance/{request_id}/cancel")
async def cancel_maintenance_request_endpoint(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRequestResponse:
    require_resident(current_user)
    return cancel_maintenance_request(db, current_user.id, request_id)


@router.get("/visitors")
async def get_visitors_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VisitorResponse]:
    require_resident(current_user)
    return get_visitors(db, current_user.id)


@router.post("/visitors")
async def create_visitor_endpoint(
    visitor: VisitorCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VisitorResponse:
    require_resident(current_user)
    return create_visitor(db, current_user.id, visitor)


@router.patch("/visitors/{visitor_id}")
async def update_visitor_status_endpoint(
    visitor_id: UUID,
    status_update: VisitorUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VisitorResponse:
    require_resident(current_user)
    return update_visitor_status(db, current_user.id, visitor_id, status_update)


@router.get("/payments")
async def get_payments_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    require_resident(current_user)
    return get_payments(db, current_user.id)


@router.post("/payments/{payment_id}/pay")
async def pay_payment_endpoint(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    require_resident(current_user)
    return pay_payment(db, current_user.id, payment_id)


@router.get("/events")
async def get_events_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EventResponse]:
    require_resident(current_user)
    return get_events(db, current_user.id)


@router.get("/forum-posts")
async def get_forum_posts_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ForumPostResponse]:
    require_resident(current_user)
    return get_forum_posts(db, current_user.id)


@router.post("/forum-posts")
async def create_forum_post_endpoint(
    post: ForumPostCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForumPostResponse:
    require_resident(current_user)
    return create_forum_post(db, current_user.id, post)
