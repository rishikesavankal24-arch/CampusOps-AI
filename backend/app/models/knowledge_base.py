"""Knowledge Base ORM Model for RAG retrieval."""

import enum
import uuid
from typing import Any
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KBCategory(str, enum.Enum):
    RUNBOOK = "runbook"
    FAQ = "faq"
    POLICY = "policy"
    DIAGNOSTIC = "diagnostic"


class KnowledgeBase(Base):
    """Knowledge base articles for RAG retrieval."""

    __tablename__ = "knowledge_base"

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
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    category: Mapped[KBCategory] = mapped_column(
        SQLEnum(KBCategory, name="kb_category_enum", values_callable=lambda x: [e.value for e in x]),
        default=KBCategory.FAQ,
        nullable=False,
        index=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    __table_args__ = (
        Index("ix_knowledge_base_category_active", "category", "is_active"),
    )

