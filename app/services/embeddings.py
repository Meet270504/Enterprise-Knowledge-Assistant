"""Embedding providers with strict provider/model isolation."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.config import Settings, get_settings


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class EmbeddingProvider(ABC):
    provider: str
    model: str
    dimensions: int

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class DemoHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed bag-of-words embeddings for local demo mode."""

    provider = "local"
    model = "demo-hash-v1"

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            vec[0] = 1.0
            return vec

        # Soften very common function words so topical terms dominate.
        stop = {
            "the", "a", "an", "and", "or", "to", "of", "in", "on", "for",
            "is", "are", "be", "with", "at", "by", "from", "as", "that",
            "this", "it", "their", "your", "our", "what", "must", "may",
        }

        def _accumulate(key: str, weight: float) -> None:
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            scale = 1.0 + (digest[9] / 255.0)
            vec[idx] += sign * weight * scale

        for token in tokens:
            weight = 0.15 if token in stop else 1.0
            _accumulate(f"u:{token}", weight)
            if len(token) >= 4 and token not in stop:
                _accumulate(f"p3:{token[:3]}", 0.35)
                _accumulate(f"s3:{token[-3:]}", 0.35)

        for a, b in zip(tokens, tokens[1:]):
            if a in stop and b in stop:
                continue
            _accumulate(f"bi:{a}_{b}", 0.85)

        for a, b, c in zip(tokens, tokens[1:], tokens[2:]):
            if a in stop and c in stop:
                continue
            _accumulate(f"tri:{a}_{b}_{c}", 0.55)

        return _l2_normalize(vec)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    provider = "openai"

    def __init__(self, api_key: str, model: str, dimensions: int = 1536) -> None:
        from langchain_openai import OpenAIEmbeddings

        self.model = model
        self.dimensions = dimensions
        self._client = OpenAIEmbeddings(
            api_key=api_key,
            model=model,
            dimensions=dimensions,
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = await self._client.aembed_documents(texts)
        return [list(map(float, v)) for v in vectors]

    async def embed_query(self, text: str) -> list[float]:
        vector = await self._client.aembed_query(text)
        return list(map(float, vector))


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    cfg = settings or get_settings()
    if cfg.effective_demo_mode:
        return DemoHashEmbeddingProvider(dimensions=cfg.demo_embedding_dimensions)
    if not cfg.openai_api_key.strip():
        raise RuntimeError(
            "OPENAI_API_KEY is required when DEMO_MODE=false. "
            "Set a key or enable DEMO_MODE for local deterministic retrieval."
        )
    return OpenAIEmbeddingProvider(
        api_key=cfg.openai_api_key,
        model=cfg.openai_embedding_model,
        dimensions=cfg.openai_embedding_dimensions,
    )


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]
