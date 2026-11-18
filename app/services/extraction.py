"""Text extraction from uploaded documents."""

from __future__ import annotations

import csv
import io
from pathlib import Path


class ExtractionError(Exception):
    """Raised when a file cannot be read into usable text."""


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from supported file bytes."""
    suffix = Path(filename).suffix.lower()
    if not data:
        raise ExtractionError("File is empty.")

    if suffix in {".txt", ".md", ".markdown"}:
        return _decode_text(data)
    if suffix == ".csv":
        return _extract_csv(data)
    if suffix == ".pdf":
        return _extract_pdf(data)
    if suffix == ".docx":
        return _extract_docx(data)
    raise ExtractionError(
        f"Unsupported file type '{suffix}'. Allowed: PDF, DOCX, TXT, Markdown, CSV."
    )


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ExtractionError("Could not decode text file as UTF-8 or Latin-1.")
    cleaned = text.strip()
    if not cleaned:
        raise ExtractionError("Text file contains no readable content.")
    return cleaned


def _extract_csv(data: bytes) -> str:
    text = _decode_text(data)
    reader = csv.reader(io.StringIO(text))
    rows: list[str] = []
    for row in reader:
        cells = [cell.strip() for cell in row if cell and cell.strip()]
        if cells:
            rows.append(" | ".join(cells))
    if not rows:
        raise ExtractionError("CSV file contains no readable rows.")
    return "\n".join(rows)


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError("PDF support is not installed (pypdf).") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Could not open PDF: {exc}") from exc

    parts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            page_text = ""
        if page_text.strip():
            parts.append(page_text.strip())

    combined = "\n\n".join(parts).strip()
    if not combined:
        raise ExtractionError(
            "No extractable text found in this PDF. Scanned or image-only PDFs "
            "require OCR before upload; this portfolio app does not run OCR."
        )
    return combined


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ExtractionError("DOCX support is not installed (python-docx).") from exc

    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Could not open DOCX: {exc}") from exc

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    # Include simple table text
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    combined = "\n\n".join(paragraphs).strip()
    if not combined:
        raise ExtractionError("DOCX file contains no readable text.")
    return combined
