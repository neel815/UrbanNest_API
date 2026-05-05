from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.admin import AdminProfile, Announcement as AnnouncementModel, Building, Unit
from app.models.resident import (
    Event,
    ForumPost,
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
    Payment,
    PaymentStatus,
    ResidentProfile,
    Visitor,
    VisitorStatus,
)
from app.models.user import User, UserRole
from app.schemas.resident import (
    AnnouncementResponse,
    DashboardStats,
    EventResponse,
    ForumPostCreateRequest,
    ForumPostResponse,
    MaintenanceCreateRequest,
    MaintenanceRequestResponse,
    PaymentResponse,
    ResidentProfileSummary,
    VisitorCreateRequest,
    VisitorResponse,
    VisitorUpdateRequest,
)


def require_resident(user: User) -> None:
    if user.role != UserRole.RESIDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resident only")


def _get_resident_profile_entity(db: Session, user_id: UUID) -> ResidentProfile:
    profile = (
        db.query(ResidentProfile)
        .options(joinedload(ResidentProfile.unit).joinedload(Unit.building))
        .filter(ResidentProfile.user_id == user_id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident profile not found")
    return profile


def _get_resident_building_id(db: Session, user_id: UUID) -> UUID | None:
    profile = _get_resident_profile_entity(db, user_id)
    return profile.unit.building_id if profile.unit is not None else None


def _announcement_query(db: Session, building_id: UUID | None = None):
    query = db.query(AnnouncementModel)
    if building_id is None:
        return query.filter(False)
    return query.filter(AnnouncementModel.building_id == building_id)


def _to_announcement_response(announcement: AnnouncementModel) -> AnnouncementResponse:
    return AnnouncementResponse.model_validate(announcement)


def _to_maintenance_response(record: MaintenanceRequest) -> MaintenanceRequestResponse:
    return MaintenanceRequestResponse.model_validate(record)


def _to_visitor_response(record: Visitor) -> VisitorResponse:
    response = VisitorResponse.model_validate(record)
    if getattr(record, "vehicle_number", None) is not None:
        response.vehicle_number = getattr(record, "vehicle_number")
    return response


def _to_payment_response(record: Payment) -> PaymentResponse:
    return PaymentResponse.model_validate(record)


def _to_event_response(record: Event) -> EventResponse:
    return EventResponse.model_validate(record)


def _to_forum_post_response(record: ForumPost) -> ForumPostResponse:
    return ForumPostResponse.model_validate(record)


def get_resident_profile(db: Session, user_id: UUID | str) -> ResidentProfileSummary:
    profile = _get_resident_profile_entity(db, UUID(str(user_id)))
    unit = profile.unit
    building_name = unit.building.name if unit and unit.building else None

    return ResidentProfileSummary(
        full_name=profile.user.full_name,
        unit_number=unit.unit_number if unit else None,
        building_name=building_name,
    )


def get_dashboard_stats(db: Session, user_id: UUID | str) -> DashboardStats:
    parsed_user_id = UUID(str(user_id))
    announcements_count = len(get_announcements(db, parsed_user_id))
    pending_maintenance = (
        db.query(func.count(MaintenanceRequest.id))
        .filter(
            MaintenanceRequest.resident_id == parsed_user_id,
            MaintenanceRequest.status.in_([MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS]),
        )
        .scalar()
        or 0
    )
    active_visitors = (
        db.query(func.count(Visitor.id))
        .filter(Visitor.resident_id == parsed_user_id, Visitor.status == VisitorStatus.CHECKED_IN)
        .scalar()
        or 0
    )
    total_due = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.resident_id == parsed_user_id,
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE]),
        )
        .scalar()
        or 0
    )

    return DashboardStats(
        announcements_count=announcements_count,
        pending_maintenance=pending_maintenance,
        active_visitors=active_visitors,
        total_due=float(total_due),
    )


def get_announcements(db: Session, user_id: UUID | str) -> list[AnnouncementResponse]:
    parsed_user_id = UUID(str(user_id))
    building_id = _get_resident_building_id(db, parsed_user_id)
    if building_id is None:
        return []

    announcements = (
        _announcement_query(db, building_id)
        .order_by(AnnouncementModel.published_at.desc(), AnnouncementModel.created_at.desc())
        .all()
    )
    return [_to_announcement_response(announcement) for announcement in announcements]


def get_maintenance_requests(db: Session, user_id: UUID | str) -> list[MaintenanceRequestResponse]:
    parsed_user_id = UUID(str(user_id))
    records = (
        db.query(MaintenanceRequest)
        .filter(MaintenanceRequest.resident_id == parsed_user_id)
        .order_by(MaintenanceRequest.created_at.desc())
        .all()
    )
    return [_to_maintenance_response(record) for record in records]


def create_maintenance_request(db: Session, user_id: UUID | str, data: MaintenanceCreateRequest) -> MaintenanceRequestResponse:
    parsed_user_id = UUID(str(user_id))
    profile = _get_resident_profile_entity(db, parsed_user_id)
    record = MaintenanceRequest(
        title=data.title,
        description=data.description,
        category=data.category,
        priority=data.priority,
        photo_url=data.photo_url,
        status=MaintenanceStatus.OPEN,
        resident_id=parsed_user_id,
        unit_id=profile.unit_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_maintenance_response(record)


def cancel_maintenance_request(db: Session, user_id: UUID | str, request_id: UUID | str) -> MaintenanceRequestResponse:
    parsed_user_id = UUID(str(user_id))
    parsed_request_id = UUID(str(request_id))
    record = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == parsed_request_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found")
    if record.resident_id != parsed_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel your own request")
    if record.status != MaintenanceStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only open requests can be cancelled")

    record.status = MaintenanceStatus.CANCELLED
    record.updated_by = parsed_user_id
    db.commit()
    db.refresh(record)
    return _to_maintenance_response(record)


def get_visitors(db: Session, user_id: UUID | str) -> list[VisitorResponse]:
    parsed_user_id = UUID(str(user_id))
    records = (
        db.query(Visitor)
        .filter(Visitor.resident_id == parsed_user_id)
        .order_by(Visitor.expected_date.desc(), Visitor.created_at.desc())
        .all()
    )
    return [_to_visitor_response(record) for record in records]


def create_visitor(db: Session, user_id: UUID | str, data: VisitorCreateRequest) -> VisitorResponse:
    parsed_user_id = UUID(str(user_id))
    record = Visitor(
        visitor_name=data.visitor_name,
        visitor_phone=data.visitor_phone,
        purpose=data.purpose,
        resident_id=parsed_user_id,
        expected_date=data.expected_date,
        status=VisitorStatus.PENDING,
    )
    setattr(record, "vehicle_number", data.vehicle_number)
    db.add(record)
    db.commit()
    db.refresh(record)
    setattr(record, "vehicle_number", data.vehicle_number)
    return _to_visitor_response(record)


def update_visitor_status(db: Session, user_id: UUID | str, visitor_id: UUID | str, data: VisitorUpdateRequest) -> VisitorResponse:
    parsed_user_id = UUID(str(user_id))
    parsed_visitor_id = UUID(str(visitor_id))
    record = (
        db.query(Visitor)
        .filter(Visitor.id == parsed_visitor_id, Visitor.resident_id == parsed_user_id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor not found")

    if data.status is not None:
        record.status = data.status
    if data.check_in_time is not None:
        record.check_in_time = data.check_in_time
    elif data.status == VisitorStatus.CHECKED_IN:
        record.check_in_time = datetime.now(timezone.utc)
    if data.check_out_time is not None:
        record.check_out_time = data.check_out_time
    elif data.status == VisitorStatus.CHECKED_OUT:
        record.check_out_time = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)
    return _to_visitor_response(record)


def get_payments(db: Session, user_id: UUID | str) -> list[PaymentResponse]:
    parsed_user_id = UUID(str(user_id))
    records = (
        db.query(Payment)
        .filter(Payment.resident_id == parsed_user_id)
        .order_by(Payment.due_date.desc(), Payment.created_at.desc())
        .all()
    )
    return [_to_payment_response(record) for record in records]


def pay_payment(db: Session, user_id: UUID | str, payment_id: UUID | str) -> PaymentResponse:
    parsed_user_id = UUID(str(user_id))
    parsed_payment_id = UUID(str(payment_id))
    record = (
        db.query(Payment)
        .filter(Payment.id == parsed_payment_id, Payment.resident_id == parsed_user_id)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    record.status = PaymentStatus.PAID
    if record.paid_date is None:
        record.paid_date = datetime.now(timezone.utc).date()
    if record.transaction_ref is None:
        record.transaction_ref = "online"
    db.commit()
    db.refresh(record)
    return _to_payment_response(record)


def get_events(db: Session, user_id: UUID | str) -> list[EventResponse]:
    parsed_user_id = UUID(str(user_id))
    building_id = _get_resident_building_id(db, parsed_user_id)
    if building_id is None:
        return []

    records = (
        db.query(Event)
        .filter(
            Event.building_id == building_id,
            Event.is_active.is_(True),
            Event.event_date >= datetime.now(timezone.utc),
        )
        .order_by(Event.event_date.asc(), Event.created_at.desc())
        .all()
    )
    return [_to_event_response(record) for record in records]


def get_forum_posts(db: Session, user_id: UUID | str) -> list[ForumPostResponse]:
    records = (
        db.query(ForumPost)
        .filter(ForumPost.is_active.is_(True))
        .order_by(ForumPost.is_pinned.desc(), ForumPost.created_at.desc(), ForumPost.upvotes.desc())
        .all()
    )
    return [_to_forum_post_response(record) for record in records]


def create_forum_post(db: Session, user_id: UUID | str, data: ForumPostCreateRequest) -> ForumPostResponse:
    parsed_user_id = UUID(str(user_id))
    record = ForumPost(
        title=data.title,
        content=data.content,
        category=data.category,
        author_id=parsed_user_id,
        is_pinned=False,
        upvotes=0,
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_forum_post_response(record)
