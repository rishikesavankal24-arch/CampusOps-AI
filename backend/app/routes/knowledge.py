"""FastAPI endpoints for Knowledge Base management, file ingestion, and testing seeds."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge_base import KBCategory, KnowledgeBase
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeDocumentItem,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeListResponse,
)
from app.services.auth_dependencies import require_support
from app.services.knowledge_service import ingest_document, seed_sample_it_knowledge

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown"}


@router.post(
    "/ingest",
    response_model=KnowledgeIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest text/markdown knowledge document",
    description="Chops document into semantic chunks, generates 768-dim embeddings via Gemini, and indexes into pgvector.",
)
async def ingest_knowledge_json(
    request: KnowledgeIngestRequest,
    current_user: User = Depends(require_support),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeIngestResponse:
    """Ingest a knowledge base article via JSON payload."""
    try:
        return await ingest_document(
            db=db,
            title=request.title,
            content=request.content,
            category=request.category,
            source=request.source,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/upload",
    response_model=KnowledgeIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload knowledge file (.txt, .md)",
    description="Uploads a plaintext or markdown file for chunking and vector storage.",
)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=2, max_length=255),
    category: KBCategory = Form(default=KBCategory.FAQ),
    current_user: User = Depends(require_support),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeIngestResponse:
    """Upload and ingest a text or markdown knowledge base file."""
    # 1. Validate file extension
    filename = file.filename or "unknown.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Only plaintext and markdown (.txt, .md) are supported.",
        )

    # 2. Read and validate content size
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 2MB limit",
        )

    try:
        content_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be valid UTF-8 encoded text",
        )

    if not content_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        return await ingest_document(
            db=db,
            title=title,
            content=content_text,
            category=category,
            source=filename,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/seed-sample",
    response_model=list[KnowledgeIngestResponse],
    summary="Seed sample campus IT runbooks and policies",
    description="Seeds realistic, verified sample runbooks for Wi-Fi, printing, password policy, and VPN for demonstration and testing.",
)
async def seed_sample_knowledge(
    current_user: User = Depends(require_support),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeIngestResponse]:
    """Seed sample runbooks into the knowledge base."""
    return await seed_sample_it_knowledge(db)


@router.get(
    "/documents",
    response_model=KnowledgeListResponse,
    summary="List ingested knowledge base documents",
    description="Returns ingested knowledge base articles and chunks.",
)
async def list_knowledge_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_support),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeListResponse:
    """List knowledge base documents."""
    count_stmt = select(func.count(KnowledgeBase.id)).where(KnowledgeBase.is_active.is_(True))
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(KnowledgeBase)
        .where(KnowledgeBase.is_active.is_(True))
        .order_by(KnowledgeBase.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    items: list[KnowledgeDocumentItem] = []
    for r in records:
        source = r.extra_metadata.get("source") if r.extra_metadata else None
        chunk_idx = r.extra_metadata.get("chunk_index") if r.extra_metadata else None
        snippet = r.content[:180] + "..." if len(r.content) > 180 else r.content
        items.append(
            KnowledgeDocumentItem(
                id=r.id,
                title=r.title,
                category=r.category.value if hasattr(r.category, "value") else str(r.category),
                source=source,
                chunk_index=chunk_idx,
                content_snippet=snippet,
                created_at=r.created_at,
            )
        )

    return KnowledgeListResponse(documents=items, total=total)

