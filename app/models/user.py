import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    ADMIN = "admin"
    RESIDENT = "resident"
    SECURITY = "security"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    must_reset_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=UserRole.RESIDENT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    resident_profile = relationship("ResidentProfile", back_populates="user", uselist=False)
    security_profile = relationship("SecurityProfile", back_populates="user", uselist=False)
    announcements = relationship("Announcement", back_populates="author")
    maintenance_requests = relationship("MaintenanceRequest", back_populates="resident")
    visitor_requests = relationship("Visitor", back_populates="resident", foreign_keys="Visitor.resident_id")
    approved_visits = relationship("Visitor", back_populates="approved_by_user", foreign_keys="Visitor.approved_by")
    payments = relationship("Payment", back_populates="resident")
    created_events = relationship("Event", back_populates="creator", foreign_keys="Event.created_by")
    forum_posts = relationship("ForumPost", back_populates="author", foreign_keys="ForumPost.author_id")
