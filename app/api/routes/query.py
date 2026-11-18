"""RAG query endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import QueryRequest, QueryResponse
from app.services.rag import answer_question

router = APIRouter(tags=["query"])


@router.post("/api/query", response_model=QueryResponse)
async def query_knowledge_base(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    return await answer_question(
        db,
        body.question,
        department=body.department,
        category=body.category,
        top_k=body.top_k,
    )
