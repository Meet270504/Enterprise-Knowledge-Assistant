"""Configurable overlapping text chunking."""

from __future__ import annotations


def split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[str]:
    """Split text into overlapping character chunks on paragraph/sentence boundaries when possible."""
    cleaned = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n"))
    cleaned = cleaned.strip()
    if not cleaned:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    length = len(cleaned)

    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            window = cleaned[start:end]
            # Prefer breaking on paragraph, then sentence, then whitespace.
            break_at = _best_break(window)
            if break_at > chunk_size * 0.4:
                end = start + break_at

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= length:
            break
        start = max(0, end - chunk_overlap)
        # Avoid infinite loop on pathological overlap
        if start >= end:
            start = end

    return chunks


def _best_break(window: str) -> int:
    for sep in ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "):
        idx = window.rfind(sep)
        if idx != -1:
            return idx + len(sep)
    return len(window)
