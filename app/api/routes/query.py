"""RAG query endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas import QueryRequest, QueryResponse
from app.services.query_limits import check_query_budget
from app.services.rag import answer_question

router = APIRouter(tags=["query"])


@router.post("/api/query", response_model=QueryResponse)
async def query_knowledge_base(
    body: QueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    check_query_budget(request, get_settings())
    return await answer_question(
        db,
        body.question,
        department=body.department,
        category=body.category,
        top_k=body.top_k,
    )
