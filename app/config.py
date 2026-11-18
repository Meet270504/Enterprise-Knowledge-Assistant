"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise Generative AI Knowledge Assistant"
    port: int = Field(default=8000, alias="PORT")
    host: str = "0.0.0.0"

    database_url: str = (
        "postgresql+asyncpg://eka:eka_secret@localhost:5432/eka"
    )
    database_url_sync: str = "postgresql://eka:eka_secret@localhost:5432/eka"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    demo_mode: bool = True
    seed_demo_documents: bool = True
    public_demo: bool = False

    max_upload_bytes: int = 10 * 1024 * 1024
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 5
    # Cosine similarity floor. Local hash embeddings score lower than OpenAI;
    # 0.12 works for demo evidence retrieval while still abstaining on noise.
    relevance_threshold: float = 0.12
    upload_dir: str = "uploads"

    # text-embedding-3-small default dimension. Demo hash vectors use the same
    # width so one pgvector column works; isolation is by provider/model labels.
    openai_embedding_dimensions: int = 1536
    demo_embedding_dimensions: int = 1536

    allowed_extensions: frozenset[str] = frozenset(
        {".pdf", ".docx", ".txt", ".md", ".markdown", ".csv"}
    )

    @field_validator("openai_chat_model")
    @classmethod
    def validate_chat_model(cls, value: str) -> str:
        allowed = {"gpt-4o-mini", "gpt-4o"}
        if value not in allowed:
            # Allow other OpenAI chat model ids for flexibility, but prefer known ones.
            return value
        return value

    @property
    def effective_demo_mode(self) -> bool:
        """Demo mode when explicitly enabled or when no OpenAI key is present."""
        if self.demo_mode:
            return True
        return not bool(self.openai_api_key.strip())

    @property
    def mode_label(self) -> Literal["local_demo", "openai"]:
        return "local_demo" if self.effective_demo_mode else "openai"

    @property
    def embedding_provider(self) -> str:
        return "local" if self.effective_demo_mode else "openai"

    @property
    def embedding_model(self) -> str:
        if self.effective_demo_mode:
            return "demo-hash-v1"
        return self.openai_embedding_model

    @property
    def embedding_dimensions(self) -> int:
        if self.effective_demo_mode:
            return self.demo_embedding_dimensions
        return self.openai_embedding_dimensions


@lru_cache
def get_settings() -> Settings:
    return Settings()
