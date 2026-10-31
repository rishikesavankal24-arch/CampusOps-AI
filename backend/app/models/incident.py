"""Incident ORM Model and Enums."""

import enum
import uuid
from typing import TYPE_CHECKING, Any
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.evidence import Evidence
    from app.models.chat_message import ChatMessage


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategory(str, enum.Enum):
    NETWORK = "network"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    ACCESS = "access"
    OTHER = "other"


class Incident(Base):
    """Incident/ticket entity."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus, name="incident_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )
    priority: Mapped[IncidentPriority] = mapped_column(
        SQLEnum(IncidentPriority, name="incident_priority_enum", values_callable=lambda x: [e.value for e in x]),
        default=IncidentPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    category: Mapped[IncidentCategory] = mapped_column(
        SQLEnum(IncidentCategory, name="incident_category_enum", values_callable=lambda x: [e.value for e in x]),
        default=IncidentCategory.OTHER,
        nullable=False,
        index=True,
    )

    reported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # AI Intelligence Artifacts
    ai_classification: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    ai_root_cause: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    ai_resolution: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User",
        back_populates="reported_incidents",
        foreign_keys=[reported_by],
    )
    assignee: Mapped["User | None"] = relationship(
        "User",
        back_populates="assigned_incidents",
        foreign_keys=[assigned_to],
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="incident",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_incidents_status_priority", "status", "priority"),
        Index("ix_incidents_reported_by_created", "reported_by", "created_at"),
    )

