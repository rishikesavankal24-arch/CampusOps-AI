"""User ORM Model and Role Definitions."""

import enum
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.chat_message import ChatMessage
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    """Authorized user roles in CampusOps AI."""
    STUDENT = "student"
    SUPPORT = "support"
    ADMIN = "admin"

    @classmethod
    def default_self_assignable_roles(cls) -> set["UserRole"]:
        """Roles that users can self-register as. ADMIN is strictly excluded."""
        return {cls.STUDENT}


class User(Base):
    """User account entity."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.STUDENT,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    reported_incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="reporter",
        foreign_keys="Incident.reported_by",
        cascade="all, delete-orphan",
    )
    assigned_incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="assignee",
        foreign_keys="Incident.assigned_to",
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="user",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )

    @property
    def is_admin(self) -> bool:
        """Check if user has administrator privileges."""
        return self.role == UserRole.ADMIN

    @property
    def is_support(self) -> bool:
        """Check if user is IT Support staff or above."""
        return self.role in {UserRole.SUPPORT, UserRole.ADMIN}

    @staticmethod
    def validate_role_transition(requester_role: UserRole, target_role: UserRole) -> bool:
        """Strict authorization logic: only active Admins can assign or change roles."""
        if requester_role != UserRole.ADMIN:
            return False
        return True

