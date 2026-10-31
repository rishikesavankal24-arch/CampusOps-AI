"""FastAPI endpoints for the AI Chatbot and RAG conversation."""

from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageItem,
    ChatQueryRequest,
    ChatQueryResponse,
    ClearHistoryResponse,
    SourceReference,
)
from app.services.auth_dependencies import get_current_user
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG"])


@router.post(
    "",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit question to Campus IT AI Assistant",
    description="Submits a campus IT troubleshooting question, retrieves knowledge base runbooks, and returns a grounded response.",
)
async def submit_chat_message(
    request: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatQueryResponse:
    """Submit a question and receive a grounded RAG response."""
    return await rag_service.answer_user_query(
        db=db,
        user_id=current_user.id,
        user_query=request.message,
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="Retrieve current user conversation history",
    description="Returns chronological message history belonging exclusively to the authenticated user.",
)
async def get_chat_history(
    limit: int = Query(50, ge=1, le=100, description="Max messages to retrieve"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    """Fetch paginated chat history for the authenticated user."""
    # Count total
    count_stmt = select(func.count(ChatMessage.id)).where(ChatMessage.user_id == current_user.id)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch messages
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    items: list[ChatMessageItem] = []
    for msg in messages:
        sources: list[SourceReference] = []
        is_grounded: bool | None = None

        if msg.tool_calls and isinstance(msg.tool_calls, dict):
            raw_sources = msg.tool_calls.get("sources", [])
            is_grounded = msg.tool_calls.get("is_grounded")
            for s in raw_sources:
                try:
                    sources.append(SourceReference(**s))
                except Exception:
                    pass

        role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
        items.append(
            ChatMessageItem(
                id=msg.id,
                role=role_str,
                content=msg.content,
                sources=sources,
                is_grounded=is_grounded,
                created_at=msg.created_at,
            )
        )

    return ChatHistoryResponse(messages=items, total=total)


@router.delete(
    "/history",
    response_model=ClearHistoryResponse,
    summary="Clear conversation history",
    description="Permanently deletes all chat message history belonging exclusively to the authenticated user.",
)
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClearHistoryResponse:
    """Delete all chat messages for the authenticated user."""
    stmt = delete(ChatMessage).where(ChatMessage.user_id == current_user.id)
    result = await db.execute(stmt)
    await db.commit()
    deleted_count = result.rowcount or 0

    return ClearHistoryResponse(
        message="Conversation history cleared successfully",
        deleted_count=deleted_count,
    )

