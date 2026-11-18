"""SQLAlchemy ORM models."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.database import Base

# Use the larger of demo/OpenAI dims for the column; queries filter by provider/model.
# pgvector Vector requires a fixed dimension at DDL time.
_MAX_DIM = max(
    get_settings().openai_embedding_dimensions,
    get_settings().demo_embedding_dimensions,
)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    department: Mapped[str] = mapped_column(String(128), nullable=False, default="General")
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="Policy")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            "embedding_provider",
            "embedding_model",
            name="uq_chunk_doc_index_embed",
        ),
        Index(
            "ix_chunks_meta_filters",
            "department",
            "category",
            "embedding_provider",
            "embedding_model",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False, default="General")
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="Policy")
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    # Pad/truncate at insert time to match column width when using smaller demo dims.
    embedding: Mapped[list[float]] = mapped_column(Vector(_MAX_DIM), nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
