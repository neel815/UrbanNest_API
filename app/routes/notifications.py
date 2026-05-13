from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.auth_service import get_current_user
from app.services.notification_service import get_notifications, mark_all_as_read, mark_as_read

router = APIRouter()


@router.get("")
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    return get_notifications(db, current_user.id)


@router.patch("/{notification_id}/read")
async def read_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    return mark_as_read(db, current_user.id, notification_id)


@router.patch("/read-all")
async def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return mark_all_as_read(db, current_user.id)