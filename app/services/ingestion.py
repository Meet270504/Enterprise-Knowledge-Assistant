"""Document upload, indexing, listing, and deletion."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import Chunk, Document
from app.services.chunking import split_text
from app.services.embeddings import get_embedding_provider
from app.services.extraction import ExtractionError, extract_text


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename or "upload.bin").name
    name = name.replace("\x00", "")
    name = _SAFE_NAME_RE.sub("_", name).strip("._") or "upload.bin"
    if len(name) > 200:
        stem = Path(name).stem[:180]
        suffix = Path(name).suffix[:20]
        name = f"{stem}{suffix}"
    return name


async def list_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, document_id: str) -> Document | None:
    return await db.get(Document, document_id)


async def delete_document(
    db: AsyncSession,
    document_id: str,
    settings: Settings | None = None,
) -> None:
    cfg = settings or get_settings()
    if cfg.public_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document deletion is disabled in public demo mode.",
        )
    document = await get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    upload_path = Path(cfg.upload_dir) / document.filename
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    await db.delete(document)
    await db.commit()
    if upload_path.exists() and upload_path.is_file():
        try:
            upload_path.unlink()
        except OSError:
            pass


async def ingest_upload(
    db: AsyncSession,
    upload: UploadFile,
    department: str,
    category: str,
    settings: Settings | None = None,
    *,
    is_sample: bool = False,
) -> Document:
    cfg = settings or get_settings()
    if cfg.public_demo and not is_sample:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Uploads are disabled in public demo mode. Only seeded fictional documents are available.",
        )

    original = upload.filename or "upload.bin"
    safe_name = sanitize_filename(original)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in cfg.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Allowed: {', '.join(sorted(cfg.allowed_extensions))}."
            ),
        )

    data = await upload.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(data) > cfg.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max upload size of {cfg.max_upload_bytes} bytes.",
        )

    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    upload_dir = Path(cfg.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / stored_name
    dest.write_bytes(data)

    embedder = get_embedding_provider(cfg)
    document = Document(
        filename=stored_name,
        original_filename=safe_name,
        content_type=upload.content_type or "",
        department=(department or "General").strip()[:128] or "General",
        category=(category or "Policy").strip()[:128] or "Policy",
        status="processing",
        file_size=len(data),
        is_sample=is_sample,
        embedding_provider=embedder.provider,
        embedding_model=embedder.model,
        meta={"source": "upload" if not is_sample else "sample"},
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    try:
        text = extract_text(safe_name, data)
        chunks = split_text(text, cfg.chunk_size, cfg.chunk_overlap)
        if not chunks:
            raise ExtractionError("No text chunks produced after splitting.")

        vectors = await embedder.embed_documents(chunks)
        chunk_rows: list[Chunk] = []
        for idx, (content, vector) in enumerate(zip(chunks, vectors)):
            chunk_rows.append(
                Chunk(
                    document_id=document.id,
                    chunk_index=idx,
                    content=content,
                    department=document.department,
                    category=document.category,
                    filename=document.original_filename,
                    embedding_provider=embedder.provider,
                    embedding_model=embedder.model,
                    embedding=vector,
                    token_estimate=max(1, len(content) // 4),
                    meta={"char_len": len(content)},
                )
            )
        db.add_all(chunk_rows)
        document.status = "ready"
        document.chunk_count = len(chunk_rows)
        document.error_message = None
        await db.commit()
        await db.refresh(document)
        return document
    except ExtractionError as exc:
        document.status = "failed"
        document.error_message = str(exc)
        document.chunk_count = 0
        await db.commit()
        await db.refresh(document)
        return document
    except Exception as exc:  # noqa: BLE001
        document.status = "failed"
        document.error_message = f"Indexing failed: {exc}"
        document.chunk_count = 0
        await db.commit()
        await db.refresh(document)
        return document


async def ingest_bytes(
    db: AsyncSession,
    *,
    filename: str,
    data: bytes,
    department: str,
    category: str,
    settings: Settings | None = None,
    is_sample: bool = False,
) -> Document:
    """Ingest from in-memory bytes (used by demo seeding)."""

    class _MemoryUpload:
        def __init__(self, name: str, payload: bytes) -> None:
            self.filename = name
            self.content_type = "text/plain"
            self._payload = payload

        async def read(self) -> bytes:
            return self._payload

    return await ingest_upload(
        db,
        _MemoryUpload(filename, data),  # type: ignore[arg-type]
        department=department,
        category=category,
        settings=settings,
        is_sample=is_sample,
    )


async def document_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Document))
    return int(result.scalar_one())
