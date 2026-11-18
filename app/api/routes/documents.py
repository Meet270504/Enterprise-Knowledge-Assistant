"""Document list, upload, and delete endpoints."""

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DocumentListResponse, DocumentOut
from app.services import ingestion

router = APIRouter(tags=["documents"])


@router.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)) -> DocumentListResponse:
    docs = await ingestion.list_documents(db)
    return DocumentListResponse(
        documents=[DocumentOut.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.post(
    "/api/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(default="General"),
    category: str = Form(default="Policy"),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    document = await ingestion.ingest_upload(
        db,
        file,
        department=department,
        category=category,
    )
    return DocumentOut.model_validate(document)


@router.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    await ingestion.delete_document(db, document_id)
