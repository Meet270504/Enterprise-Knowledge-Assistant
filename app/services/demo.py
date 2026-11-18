"""Seed fictional sample documents for local / public demo mode."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import Document
from app.services.ingestion import ingest_bytes

logger = logging.getLogger(__name__)

SAMPLE_SPECS: list[dict[str, str]] = [
    {
        "filename": "pto_policy.md",
        "department": "Human Resources",
        "category": "Benefits",
    },
    {
        "filename": "security_policy.md",
        "department": "Security",
        "category": "Security",
    },
    {
        "filename": "remote_work_policy.md",
        "department": "Human Resources",
        "category": "Workplace",
    },
    {
        "filename": "travel_expense_policy.md",
        "department": "Finance",
        "category": "Expenses",
    },
    {
        "filename": "onboarding_checklist.txt",
        "department": "Human Resources",
        "category": "Onboarding",
    },
]


def sample_docs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "sample_docs"


async def seed_demo_documents(
    db: AsyncSession,
    settings: Settings | None = None,
) -> int:
    """Insert sample docs when seeding is enabled and none exist yet for this embedding space."""
    cfg = settings or get_settings()
    if not cfg.seed_demo_documents:
        return 0

    # Count samples already present for the active embedding provider/model
    result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(Document.is_sample.is_(True))
        .where(Document.embedding_provider == cfg.embedding_provider)
        .where(Document.embedding_model == cfg.embedding_model)
    )
    existing = int(result.scalar_one())
    if existing > 0:
        logger.info("Demo samples already present (%s); skipping seed.", existing)
        return 0

    docs_dir = sample_docs_dir()
    seeded = 0
    for spec in SAMPLE_SPECS:
        path = docs_dir / spec["filename"]
        if not path.exists():
            logger.warning("Sample document missing: %s", path)
            continue
        data = path.read_bytes()
        document = await ingest_bytes(
            db,
            filename=spec["filename"],
            data=data,
            department=spec["department"],
            category=spec["category"],
            settings=cfg,
            is_sample=True,
        )
        logger.info(
            "Seeded sample %s status=%s chunks=%s",
            document.original_filename,
            document.status,
            document.chunk_count,
        )
        seeded += 1
    return seeded
