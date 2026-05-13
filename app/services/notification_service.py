from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationListResponse, NotificationResponse


def create_notification(
    db: Session,
    user_id: UUID,
    title: str,
    message: str,
    type: NotificationType,
    related_id: UUID | None = None,
    related_type: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        is_read=False,
        related_id=related_id,
        related_type=related_type,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notifications(db: Session, user_id: UUID) -> NotificationListResponse:
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    unread_count = db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read.is_(False)).count()
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(notification) for notification in notifications],
        unread_count=unread_count,
    )


def mark_as_read(db: Session, user_id: UUID, notification_id: UUID) -> NotificationResponse:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Notification does not belong to you")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return NotificationResponse.model_validate(notification)


def mark_all_as_read(db: Session, user_id: UUID) -> dict:
    db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read.is_(False)).update(
        {Notification.is_read: True}, synchronize_session=False
    )
    db.commit()
    return {"message": "All marked as read"}