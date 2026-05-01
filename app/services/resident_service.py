from datetime import datetime, timezone
from itertools import count
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.admin import Announcement as ResidentAnnouncement
from app.models.user import User, UserRole
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

_maintenance_id_gen = count(1)
_visitor_id_gen = count(1)
_payment_id_gen = count(1)
_event_id_gen = count(1)
_forum_post_id_gen = count(1)

_maintenance_store: dict[str, list[dict]] = {}
_visitors_store: dict[str, list[dict]] = {}
_payments_store: dict[str, list[dict]] = {}
_events_store: dict[str, list[dict]] = {}
_forum_posts_store: dict[str, list[dict]] = {}


def _resident_key(user_id: UUID | str) -> str:
    return str(user_id)


def require_resident(user: User) -> None:
    if user.role != UserRole.RESIDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resident only")


def _get_announcements_for_resident(db: Session) -> list[Announcement]:
    announcements = (
        db.query(ResidentAnnouncement)
        .order_by(ResidentAnnouncement.published_at.desc(), ResidentAnnouncement.created_at.desc())
        .limit(5)
        .all()
    )
    return [
        Announcement(
            id=str(announcement.id),
            title=announcement.title,
            content=announcement.content,
            date=announcement.published_at.date().isoformat(),
            priority=announcement.priority.value if hasattr(announcement.priority, "value") else str(announcement.priority),
            author=announcement.author.full_name if announcement.author else "Management Team",
        )
        for announcement in announcements
    ]


def get_resident_profile(db: Session, user_id: UUID | str) -> ResidentProfileSummary:
    resident_user = (
        db.query(User)
        .options(joinedload(User.resident_profile).joinedload("unit").joinedload("building"))
        .filter(User.id == user_id)
        .first()
    )
    if not resident_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    profile = resident_user.resident_profile
    unit = profile.unit if profile else None
    building = unit.building if unit else None
    building_name = building.name if building else None

    return ResidentProfileSummary(
        full_name=resident_user.full_name,
        unit_number=unit.unit_number if unit else None,
        building_name=building_name,
        society_name=building_name,
    )


def get_dashboard_stats(db: Session, user_id: UUID | str) -> DashboardStats:
    key = _resident_key(user_id)
    maintenance = _maintenance_store.get(key, [])
    visitors = _visitors_store.get(key, [])
    payments = _payments_store.get(key, [])
    announcements = _get_announcements_for_resident(db)

    pending_maintenance = len([item for item in maintenance if item.get("status") in {"pending", "in_progress"}])
    active_visitors = len([item for item in visitors if item.get("status") == "checked_in"])
    total_due = sum(
        float(item.get("amount", 0))
        for item in payments
        if item.get("status") in {"pending", "overdue"}
    )

    return DashboardStats(
        announcements_count=len(announcements),
        pending_maintenance=pending_maintenance,
        active_visitors=active_visitors,
        total_due=round(total_due, 2),
    )


def get_announcements(db: Session, building_id: UUID | str | None = None) -> list[Announcement]:
    return _get_announcements_for_resident(db)


def get_maintenance_requests(db: Session, user_id: UUID | str) -> list[MaintenanceRequest]:
    key = _resident_key(user_id)
    return [MaintenanceRequest(**item) for item in _maintenance_store.get(key, [])]


def create_maintenance_request(db: Session, user_id: UUID | str, data: MaintenanceCreateRequest) -> MaintenanceRequest:
    key = _resident_key(user_id)
    now_iso_date = datetime.now(timezone.utc).date().isoformat()
    new_item = {
        "id": next(_maintenance_id_gen),
        "title": data.title,
        "description": data.description,
        "category": data.category,
        "priority": data.priority,
        "status": "pending",
        "date": now_iso_date,
        "lastUpdated": now_iso_date,
    }
    _maintenance_store.setdefault(key, []).insert(0, new_item)
    return MaintenanceRequest(**new_item)


def update_maintenance_request(db: Session, request_id: int, data: dict[str, Any]) -> MaintenanceRequest:
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    key = _resident_key(user_id)
    resident_requests = _maintenance_store.get(key, [])
    target = next((item for item in resident_requests if item.get("id") == request_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")

    for field in ("title", "description", "category", "priority", "status"):
        if field in data and data[field] is not None:
            target[field] = data[field]
    target["lastUpdated"] = datetime.now(timezone.utc).date().isoformat()
    return MaintenanceRequest(**target)


def get_visitors(db: Session, user_id: UUID | str) -> list[Visitor]:
    key = _resident_key(user_id)
    return [Visitor(**item) for item in _visitors_store.get(key, [])]


def create_visitor(db: Session, user_id: UUID | str, data: VisitorCreateRequest) -> Visitor:
    key = _resident_key(user_id)
    new_item = {
        "id": next(_visitor_id_gen),
        "name": data.name,
        "purpose": data.purpose,
        "date": data.date,
        "timeIn": data.timeIn,
        "timeOut": None,
        "status": "expected",
        "contactNumber": data.contactNumber,
        "vehicleNumber": data.vehicleNumber,
    }
    _visitors_store.setdefault(key, []).insert(0, new_item)
    return Visitor(**new_item)


def update_visitor(db: Session, visitor_id: int, data: dict[str, Any]) -> Visitor:
    user_id = data.get("user_id")
    status_update = data.get("status")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    if not status_update:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status is required")

    key = _resident_key(user_id)
    resident_visitors = _visitors_store.get(key, [])
    target = next((item for item in resident_visitors if item.get("id") == visitor_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found")

    target["status"] = status_update
    if status_update == "checked_out":
        target["timeOut"] = datetime.now(timezone.utc).strftime("%H:%M")
    return Visitor(**target)


def update_visitor_status(db: Session, user_id: UUID | str, visitor_id: int, status_update: VisitorStatusUpdateRequest) -> Visitor:
    return update_visitor(
        db,
        visitor_id,
        {
            "user_id": user_id,
            "status": status_update.status,
        },
    )


def get_payments(db: Session, user_id: UUID | str) -> list[Payment]:
    key = _resident_key(user_id)
    return [Payment(**item) for item in _payments_store.get(key, [])]


def pay_payment(db: Session, user_id: UUID | str, payment_id: int) -> Payment:
    key = _resident_key(user_id)
    resident_payments = _payments_store.get(key, [])
    target = next((item for item in resident_payments if item.get("id") == payment_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    target["status"] = "paid"
    target["paidDate"] = datetime.now(timezone.utc).date().isoformat()
    target["paymentMethod"] = "online"
    return Payment(**target)


def get_events(db: Session, building_id: UUID | str | None = None) -> list[Event]:
    key = _resident_key(building_id) if building_id is not None else ""
    return [Event(**item) for item in _events_store.get(key, [])]


def register_for_event(db: Session, user_id: UUID | str, event_id: int) -> Event:
    key = _resident_key(user_id)
    resident_events = _events_store.get(key, [])
    target = next((item for item in resident_events if item.get("id") == event_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if not target.get("isRegistered"):
        target["isRegistered"] = True
        target["attendees"] = int(target.get("attendees", 0)) + 1
    return Event(**target)


def get_forum_posts(db: Session, building_id: UUID | str | None = None) -> list[ForumPost]:
    key = _resident_key(building_id) if building_id is not None else ""
    return [ForumPost(**item) for item in _forum_posts_store.get(key, [])]


def create_forum_post(db: Session, user_id: UUID | str, data: ForumPostCreateRequest, full_name: str) -> ForumPost:
    key = _resident_key(user_id)
    today = datetime.now(timezone.utc).date().isoformat()
    new_item = {
        "id": next(_forum_post_id_gen),
        "title": data.title,
        "content": data.content,
        "author": full_name,
        "date": today,
        "category": data.category,
        "replies": 0,
        "lastActivity": today,
    }
    _forum_posts_store.setdefault(key, []).insert(0, new_item)
    return ForumPost(**new_item)
