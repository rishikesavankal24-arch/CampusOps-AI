"""Pydantic schemas for AI Chatbot and RAG conversations."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ChatQueryRequest(BaseModel):
    """Incoming user chat query."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Campus IT question or troubleshooting query",
    )

    model_config = ConfigDict(extra="forbid")


class SourceReference(BaseModel):
    """Source reference retrieved from the knowledge base."""
    id: UUID
    title: str
    category: str
    similarity: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    snippet: str
    source_file: str | None = None


class ChatQueryResponse(BaseModel):
    """Grounded AI response with retrieved knowledge sources."""
    message_id: UUID
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    is_grounded: bool = Field(..., description="Whether response is verified against campus knowledge base")
    insufficient_context: bool = Field(
        ...,
        description="True if knowledge base did not contain enough verified information",
    )
    created_at: datetime


class ChatMessageItem(BaseModel):
    """Individual message in conversation history."""
    id: UUID
    role: str
    content: str
    sources: list[SourceReference] = Field(default_factory=list)
    is_grounded: bool | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    """User conversation history response."""
    messages: list[ChatMessageItem]
    total: int


class ClearHistoryResponse(BaseModel):
    """Response when user clears their chat history."""
    message: str
    deleted_count: int

