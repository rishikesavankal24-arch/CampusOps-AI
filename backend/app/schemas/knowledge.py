"""Pydantic schemas for Knowledge Base ingestion and management."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.knowledge_base import KBCategory


class KnowledgeIngestRequest(BaseModel):
    """Schema for direct text/markdown knowledge ingestion."""
    title: str = Field(..., min_length=2, max_length=255, description="Document title")
    content: str = Field(..., min_length=10, max_length=500000, description="Raw document text or markdown")
    category: KBCategory = Field(default=KBCategory.FAQ, description="Knowledge base classification category")
    source: str | None = Field(default=None, max_length=255, description="Originating file name or system identifier")

    model_config = ConfigDict(extra="forbid")


class KnowledgeIngestResponse(BaseModel):
    """Result of document chunking and vector ingestion."""
    document_title: str
    category: str
    chunks_ingested: int
    chunks_skipped: int
    message: str


class KnowledgeDocumentItem(BaseModel):
    """Summary of a knowledge base record/chunk."""
    id: UUID
    title: str
    category: str
    source: str | None = None
    chunk_index: int | None = None
    content_snippet: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeListResponse(BaseModel):
    """List of ingested knowledge documents."""
    documents: list[KnowledgeDocumentItem]
    total: int

