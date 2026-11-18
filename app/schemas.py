"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    mode: Literal["local_demo", "openai"]
    database: str
    app: str
    version: str


class ConfigResponse(BaseModel):
    app_name: str
    mode: Literal["local_demo", "openai"]
    chat_model: Optional[str]
    embedding_provider: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    relevance_threshold: float
    max_upload_bytes: int
    allowed_extensions: list[str]
    public_demo: bool
    uploads_enabled: bool
    deletions_enabled: bool
    seed_demo_documents: bool
    disclaimer: str


class DocumentOut(BaseModel):
    id: str
    filename: str
    original_filename: str
    department: str
    category: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    file_size: int
    is_sample: bool
    embedding_provider: str
    embedding_model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    department: Optional[str] = Field(default=None, max_length=128)
    category: Optional[str] = Field(default=None, max_length=128)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class SourcePassage(BaseModel):
    source_id: str
    document_id: str
    filename: str
    department: str
    category: str
    chunk_index: int
    content: str
    similarity: float
    citation_marker: str


class QueryResponse(BaseModel):
    answer: str
    abstained: bool
    retrieval_mode: Literal["local_demo", "openai"]
    question: str
    sources: list[SourcePassage]
    citations_used: list[str]
    filters: dict[str, Any]
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
