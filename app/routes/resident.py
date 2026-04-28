from datetime import datetime, timezone
from itertools import count
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resident import Announcement as ResidentAnnouncement
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user

router = APIRouter()

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


def _resident_key(user: User) -> str:
    return str(user.id)


def _require_resident(user: User) -> None:
    if user.role != UserRole.RESIDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resident only")

# Pydantic Models
class DashboardStats(BaseModel):
    announcements_count: int
    pending_maintenance: int
    active_visitors: int
    total_due: float

class Announcement(BaseModel):
    id: str
    title: str
    content: str
    date: str
    priority: str
    author: str

class MaintenanceRequest(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    date: str
    lastUpdated: str


class MaintenanceCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=5, max_length=1000)
    category: str = Field(min_length=2, max_length=80)
    priority: str = Field(pattern="^(low|medium|high)$")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

class Visitor(BaseModel):
    id: int
    name: str
    purpose: str
    date: str
    timeIn: str
    timeOut: Optional[str]
    status: str
    contactNumber: str
    vehicleNumber: Optional[str]


class VisitorCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    purpose: str = Field(min_length=2, max_length=200)
    date: str
    timeIn: str
    contactNumber: str = Field(min_length=5, max_length=30)
    vehicleNumber: Optional[str] = None


class VisitorStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(checked_in|checked_out)$")

class Payment(BaseModel):
    id: int
    type: str
    description: str
    amount: float
    dueDate: str
    status: str
    paidDate: Optional[str]
    paymentMethod: Optional[str]

class Event(BaseModel):
    id: int
    title: str
    description: str
    date: str
    time: str
    location: str
    type: str
    attendees: int
    maxAttendees: Optional[int]
    isRegistered: bool

class ForumPost(BaseModel):
    id: int
    title: str
    content: str
    author: str
    date: str
    category: str
    replies: int
    lastActivity: str


class ForumPostCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=5, max_length=3000)
    category: str = Field(pattern="^(general|complaints|suggestions|marketplace)$")


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

# Dashboard endpoints
@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    _require_resident(current_user)
    key = _resident_key(current_user)
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

# Announcements endpoints
@router.get("/announcements")
async def get_announcements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Announcement]:
    _require_resident(current_user)
    return _get_announcements_for_resident(db)

# Maintenance endpoints
@router.get("/maintenance")
async def get_maintenance_requests(current_user: User = Depends(get_current_user)) -> list[MaintenanceRequest]:
    _require_resident(current_user)
    key = _resident_key(current_user)
    return [MaintenanceRequest(**item) for item in _maintenance_store.get(key, [])]

@router.post("/maintenance")
async def create_maintenance_request(
    request: MaintenanceCreateRequest,
    current_user: User = Depends(get_current_user)
) -> MaintenanceRequest:
    _require_resident(current_user)
    key = _resident_key(current_user)
    now_iso_date = datetime.now(timezone.utc).date().isoformat()
    new_item = {
        "id": next(_maintenance_id_gen),
        "title": request.title,
        "description": request.description,
        "category": request.category,
        "priority": request.priority,
        "status": "pending",
        "date": now_iso_date,
        "lastUpdated": now_iso_date,
    }
    _maintenance_store.setdefault(key, []).insert(0, new_item)
    return MaintenanceRequest(**new_item)

# Visitors endpoints
@router.get("/visitors")
async def get_visitors(current_user: User = Depends(get_current_user)) -> list[Visitor]:
    _require_resident(current_user)
    key = _resident_key(current_user)
    return [Visitor(**item) for item in _visitors_store.get(key, [])]

@router.post("/visitors")
async def create_visitor(
    visitor: VisitorCreateRequest,
    current_user: User = Depends(get_current_user)
) -> Visitor:
    _require_resident(current_user)
    key = _resident_key(current_user)
    new_item = {
        "id": next(_visitor_id_gen),
        "name": visitor.name,
        "purpose": visitor.purpose,
        "date": visitor.date,
        "timeIn": visitor.timeIn,
        "timeOut": None,
        "status": "expected",
        "contactNumber": visitor.contactNumber,
        "vehicleNumber": visitor.vehicleNumber,
    }
    _visitors_store.setdefault(key, []).insert(0, new_item)
    return Visitor(**new_item)

@router.patch("/visitors/{visitor_id}")
async def update_visitor_status(
    visitor_id: int,
    status_update: VisitorStatusUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Visitor:
    _require_resident(current_user)
    key = _resident_key(current_user)
    resident_visitors = _visitors_store.get(key, [])
    target = next((item for item in resident_visitors if item.get("id") == visitor_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found")

    target["status"] = status_update.status
    if status_update.status == "checked_out":
        target["timeOut"] = datetime.now(timezone.utc).strftime("%H:%M")
    return Visitor(**target)

# Payments endpoints
@router.get("/payments")
async def get_payments(current_user: User = Depends(get_current_user)) -> list[Payment]:
    _require_resident(current_user)
    key = _resident_key(current_user)
    return [Payment(**item) for item in _payments_store.get(key, [])]

@router.post("/payments/{payment_id}/pay")
async def pay_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user)
) -> Payment:
    _require_resident(current_user)
    key = _resident_key(current_user)
    resident_payments = _payments_store.get(key, [])
    target = next((item for item in resident_payments if item.get("id") == payment_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    target["status"] = "paid"
    target["paidDate"] = datetime.now(timezone.utc).date().isoformat()
    target["paymentMethod"] = "online"
    return Payment(**target)

# Community endpoints
@router.get("/events")
async def get_events(current_user: User = Depends(get_current_user)) -> list[Event]:
    _require_resident(current_user)
    key = _resident_key(current_user)
    return [Event(**item) for item in _events_store.get(key, [])]

@router.post("/events/{event_id}/register")
async def register_for_event(
    event_id: int,
    current_user: User = Depends(get_current_user)
) -> Event:
    _require_resident(current_user)
    key = _resident_key(current_user)
    resident_events = _events_store.get(key, [])
    target = next((item for item in resident_events if item.get("id") == event_id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if not target.get("isRegistered"):
        target["isRegistered"] = True
        target["attendees"] = int(target.get("attendees", 0)) + 1
    return Event(**target)

@router.get("/forum-posts")
async def get_forum_posts(current_user: User = Depends(get_current_user)) -> list[ForumPost]:
    _require_resident(current_user)
    key = _resident_key(current_user)
    return [ForumPost(**item) for item in _forum_posts_store.get(key, [])]

@router.post("/forum-posts")
async def create_forum_post(
    post: ForumPostCreateRequest,
    current_user: User = Depends(get_current_user)
) -> ForumPost:
    _require_resident(current_user)
    key = _resident_key(current_user)
    today = datetime.now(timezone.utc).date().isoformat()
    new_item = {
        "id": next(_forum_post_id_gen),
        "title": post.title,
        "content": post.content,
        "author": current_user.full_name,
        "date": today,
        "category": post.category,
        "replies": 0,
        "lastActivity": today,
    }
    _forum_posts_store.setdefault(key, []).insert(0, new_item)
    return ForumPost(**new_item)
