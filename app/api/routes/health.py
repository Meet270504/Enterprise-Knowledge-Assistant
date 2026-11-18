"""Health and configuration endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import get_settings
from app.database import get_db
from app.schemas import ConfigResponse, HealthResponse

router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        mode=settings.mode_label,
        database=db_status,
        app=settings.app_name,
        version=__version__,
    )


@router.get("/api/config", response_model=ConfigResponse)
async def config() -> ConfigResponse:
    settings = get_settings()
    uploads_enabled = not settings.public_demo
    return ConfigResponse(
        app_name=settings.app_name,
        mode=settings.mode_label,
        chat_model=None if settings.effective_demo_mode else settings.openai_chat_model,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k=settings.top_k,
        relevance_threshold=settings.relevance_threshold,
        max_upload_bytes=settings.max_upload_bytes,
        allowed_extensions=sorted(settings.allowed_extensions),
        public_demo=settings.public_demo,
        uploads_enabled=uploads_enabled,
        deletions_enabled=uploads_enabled,
        seed_demo_documents=settings.seed_demo_documents,
        disclaimer=(
            "Do not rely on AI answers without checking the cited sources. "
            "This portfolio app is single-tenant and is not suitable for confidential "
            "enterprise data (no sign-in, RBAC, or tenant isolation)."
        ),
    )
