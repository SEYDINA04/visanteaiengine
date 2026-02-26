"""
RAG Pydantic models: Document, chunks, and RAG responses with source citations.

All RAG responses cite the Ghana Standard Treatment Guidelines (7th Edition, 2017).
"""

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    """Source citation: document name + page (from Ghana STG)."""

    document_name: str = Field(
        ...,
        description="Official document name, e.g. Ghana STG 7th Ed. 2017",
    )
    page: int | None = Field(default=None, description="Page number if available")


class DocumentChunk(BaseModel):
    """A single retrieved chunk with metadata."""

    content: str = Field(..., description="Chunk text content")
    chunk_id: str = Field(default="", description="Chunk identifier")
    page: int | None = Field(default=None, description="Page number in source document")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class RAGResponse(BaseModel):
    """Structured RAG response with answer and sources."""

    answer: str = Field(..., description="Synthesized answer from guidelines")
    sources: list[SourceCitation] = Field(
        default_factory=list,
        description="Source citations (document name + page)",
    )
    chunk_ids: list[str] = Field(
        default_factory=list,
        description="IDs of chunks used",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the answer based on retrieval",
    )
