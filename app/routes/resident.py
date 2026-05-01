from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resident import (
    Announcement,
    DashboardStats,
    Event,
    ForumPost,
    ForumPostCreateRequest,
    MaintenanceCreateRequest,
    MaintenanceRequest,
    Payment,
    ResidentProfileSummary,
    Visitor,
    VisitorCreateRequest,
    VisitorStatusUpdateRequest,
)
from app.services.auth_service import get_current_user
from app.services.resident_service import (
    create_forum_post,
    create_maintenance_request,
    create_visitor,
    get_announcements,
    get_dashboard_stats,
    get_events,
    get_forum_posts,
    get_maintenance_requests,
    get_payments,
    get_resident_profile,
    get_visitors,
    pay_payment,
    register_for_event,
    require_resident,
    update_visitor_status,
)

router = APIRouter()


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResidentProfileSummary:
    require_resident(current_user)
    return get_resident_profile(db, current_user.id)


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
) -> list[Announcement]:
    require_resident(current_user)
    return get_announcements(db, None)


@router.get("/maintenance")
async def get_maintenance_requests_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceRequest]:
    require_resident(current_user)
    return get_maintenance_requests(db, current_user.id)


@router.post("/maintenance")
async def create_maintenance_request_endpoint(
    request: MaintenanceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRequest:
    require_resident(current_user)
    return create_maintenance_request(db, current_user.id, request)


@router.get("/visitors")
async def get_visitors_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Visitor]:
    require_resident(current_user)
    return get_visitors(db, current_user.id)


@router.post("/visitors")
async def create_visitor_endpoint(
    visitor: VisitorCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Visitor:
    require_resident(current_user)
    return create_visitor(db, current_user.id, visitor)


@router.patch("/visitors/{visitor_id}")
async def update_visitor_status_endpoint(
    visitor_id: int,
    status_update: VisitorStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Visitor:
    require_resident(current_user)
    return update_visitor_status(db, current_user.id, visitor_id, status_update)


@router.get("/payments")
async def get_payments_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Payment]:
    require_resident(current_user)
    return get_payments(db, current_user.id)


@router.post("/payments/{payment_id}/pay")
async def pay_payment_endpoint(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Payment:
    require_resident(current_user)
    return pay_payment(db, current_user.id, payment_id)


@router.get("/events")
async def get_events_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Event]:
    require_resident(current_user)
    return get_events(db, current_user.id)


@router.post("/events/{event_id}/register")
async def register_for_event_endpoint(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Event:
    require_resident(current_user)
    return register_for_event(db, current_user.id, event_id)


@router.get("/forum-posts")
async def get_forum_posts_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ForumPost]:
    require_resident(current_user)
    return get_forum_posts(db, current_user.id)


@router.post("/forum-posts")
async def create_forum_post_endpoint(
    post: ForumPostCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForumPost:
    require_resident(current_user)
    return create_forum_post(db, current_user.id, post, current_user.full_name)
