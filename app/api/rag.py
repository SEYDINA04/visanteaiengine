"""
RAG API - Query Ghana Standard Treatment Guidelines.

Structured JSON responses with source citations (document name + page).
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.manager import RAGManager
from app.rag.models import RAGResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG - Guidelines"])

_rag_manager = RAGManager()


class RAGQueryRequest(BaseModel):
    """Request body for POST /api/v1/rag/query."""

    query: str = Field(..., min_length=1, description="Medical or treatment question")
    top_k: int | None = Field(default=None, ge=1, le=20, description="Number of chunks to retrieve")
    use_llm_synthesis: bool = Field(
        default=True,
        description="If true, synthesize answer with LLM; else return top chunk excerpt",
    )


@router.post(
    "/query",
    response_model=RAGResponse,
    summary="Query guidelines",
    description="Retrieve an answer from the Ghana Standard Treatment Guidelines (7th Ed., 2017). "
    "Response includes source citations (document name + page).",
)
async def rag_query(request: RAGQueryRequest) -> RAGResponse:
    """Query the Ghana STG and return structured answer with sources."""
    try:
        return await _rag_manager.answer_with_sources(
            query=request.query,
            top_k=request.top_k,
            use_llm_synthesis=request.use_llm_synthesis,
        )
    except Exception as e:
        logger.exception("RAG query error: %s", e)
        raise HTTPException(status_code=500, detail="Guidelines query failed.") from e
