"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import documents, health, query
from app.config import get_settings
from app.database import AsyncSessionLocal, close_db, init_db
from app.services.demo import seed_demo_documents
from app.services.rag import ensure_vector_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("eka")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    logger.info(
        "Starting %s mode=%s public_demo=%s",
        settings.app_name,
        settings.mode_label,
        settings.public_demo,
    )
    await init_db()
    async with AsyncSessionLocal() as session:
        await ensure_vector_index(session)
        seeded = await seed_demo_documents(session, settings)
        if seeded:
            logger.info("Seeded %s demo documents", seeded)
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Document Q&A with RAG over PostgreSQL/pgvector. "
            "Portfolio / single-tenant demo — not for confidential enterprise data."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.include_router(health.router)
    application.include_router(documents.router)
    application.include_router(query.router)

    if STATIC_DIR.exists():
        application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @application.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return application


app = create_app()


def run() -> None:
    """CLI entry used by `python -m app.main` and Docker CMD."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
