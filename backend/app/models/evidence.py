"""Evidence ORM Model with pgvector embedding support."""

import enum
import uuid
from typing import TYPE_CHECKING, Any
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.incident import Incident


class EvidenceType(str, enum.Enum):
    LOG = "log"
    SCREENSHOT = "screenshot"
    CONFIG = "config"
    NETWORK_CAPTURE = "network_capture"
    USER_REPORT = "user_report"


class Evidence(Base):
    """Evidence artifact attached to an incident."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        SQLEnum(EvidenceType, name="evidence_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    # Gemini text-embedding-004 vector dimension is 768
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    incident: Mapped["Incident"] = relationship(
        "Incident",
        back_populates="evidence",
    )

    __table_args__ = (
        Index("ix_evidence_incident_type", "incident_id", "evidence_type"),
    )

