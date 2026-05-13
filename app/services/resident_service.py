import logging
from datetime import date, datetime, time, timezone
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
from app.models.notification import NotificationType
from app.models.security import SecurityProfile
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
    ResidentProfileResponse,
    ResidentProfileSummary,
    ResidentProfileUpdateRequest,
    VisitorCreateRequest,
    VisitorResponse,
    VisitorUpdateRequest,
)
from app.services.notification_service import create_notification


logger = logging.getLogger(__name__)


def require_resident(user: User) -> None:
    if user.role != UserRole.RESIDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resident only")


def _get_resident_profile_entity(db: Session, user_id: UUID) -> ResidentProfile:
    profile = _get_resident_profile_entity_optional(db, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident profile not found")
    return profile


def _get_resident_profile_entity_optional(db: Session, user_id: UUID) -> ResidentProfile | None:
    return (
        db.query(ResidentProfile)
        .options(joinedload(ResidentProfile.unit).joinedload(Unit.building))
        .filter(ResidentProfile.user_id == user_id)
        .first()
    )


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


def _to_resident_profile_response(user: User, profile: ResidentProfile | None) -> ResidentProfileResponse:
    unit = profile.unit if profile else None
    building = unit.building if unit else None
    status = "active" if profile else "inactive"

    return ResidentProfileResponse(
        id=profile.id if profile else user.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        profile_image=user.profile_image,
        unit_number=unit.unit_number if unit else None,
        floor=unit.floor if unit else None,
        plot_number=unit.plot_number if unit else None,
        building_name=building.name if building else None,
        move_in_date=profile.move_in_date.date() if profile and profile.move_in_date else None,
        lease_end_date=profile.move_out_date.date() if profile and profile.move_out_date else None,
        emergency_contact_name=profile.emergency_contact_name if profile else None,
        emergency_contact_phone=profile.emergency_contact_phone if profile else None,
        status=status,
        created_at=profile.created_at if profile else user.created_at,
        updated_at=profile.updated_at if profile else user.updated_at,
    )


def _safe_create_notification(
    db: Session,
    user_id: UUID,
    title: str,
    message: str,
    type: NotificationType,
    related_id: UUID | None = None,
    related_type: str | None = None,
) -> None:
    try:
        create_notification(db, user_id, title, message, type, related_id=related_id, related_type=related_type)
    except Exception as exc:
        logger.error(f"Notification failed: {exc}")


def get_resident_profile(db: Session, user_id: UUID | str) -> ResidentProfileResponse:
    parsed_user_id = UUID(str(user_id))
    user = db.query(User).filter(User.id == parsed_user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    profile = _get_resident_profile_entity_optional(db, parsed_user_id)
    return _to_resident_profile_response(user, profile)


def update_resident_profile(db: Session, user_id: UUID | str, data: ResidentProfileUpdateRequest) -> ResidentProfileResponse:
    parsed_user_id = UUID(str(user_id))
    user = db.query(User).filter(User.id == parsed_user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    profile = _get_resident_profile_entity(db, parsed_user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.emergency_contact_name is not None:
        profile.emergency_contact_name = data.emergency_contact_name
    if data.emergency_contact_phone is not None:
        profile.emergency_contact_phone = data.emergency_contact_phone
    if data.move_in_date is not None:
        profile.move_in_date = datetime.combine(data.move_in_date, time.min, tzinfo=timezone.utc)
    if data.lease_end_date is not None:
        profile.move_out_date = datetime.combine(data.lease_end_date, time.min, tzinfo=timezone.utc)

    db.commit()
    db.refresh(user)
    db.refresh(profile)
    return _to_resident_profile_response(user, profile)


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
    try:
        if profile.unit and profile.unit.building_id is not None:
            admin_profile = db.query(AdminProfile).filter(AdminProfile.building_id == profile.unit.building_id).first()
            if admin_profile is not None:
                _safe_create_notification(
                    db,
                    user_id=admin_profile.user_id,
                    title="New Maintenance Request",
                    message=f"{profile.user.full_name} raised a maintenance request: {record.title}",
                    type=NotificationType.NEW_MAINTENANCE,
                    related_id=record.id,
                    related_type="maintenance",
                )
    except Exception as exc:
        logger.error(f"Notification failed: {exc}")
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
    profile = _get_resident_profile_entity(db, parsed_user_id)
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
    try:
        if profile.unit and profile.unit.building_id is not None:
            guards = db.query(SecurityProfile).filter(SecurityProfile.assigned_building_id == profile.unit.building_id).all()
            for guard in guards:
                _safe_create_notification(
                    db,
                    user_id=guard.user_id,
                    title="New Visitor Registered",
                    message=f"{record.visitor_name} expected at {record.expected_date} for {profile.user.full_name}",
                    type=NotificationType.NEW_VISITOR,
                    related_id=record.id,
                    related_type="visitor",
                )
    except Exception as exc:
        logger.error(f"Notification failed: {exc}")
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
        if data.status == VisitorStatus.CHECKED_IN and record.status != VisitorStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Visitor must be approved before check-in",
            )
        if data.status == VisitorStatus.CHECKED_OUT and record.status != VisitorStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Visitor must be checked in before check-out",
            )
        if data.status in (VisitorStatus.APPROVED, VisitorStatus.DENIED) and record.status == VisitorStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only security can approve or deny visitor status",
            )
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
