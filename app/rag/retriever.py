"""
Retriever - Retrieve top-K relevant chunks from the vector store.

Queries Chroma with the user question and returns ranked chunks from
Ghana Standard Treatment Guidelines.
"""

import logging
from typing import List

from app.core.config import settings
from app.core.vectorstore import ChromaVectorStore, get_vector_store
from app.rag.models import DocumentChunk, SourceCitation

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieves relevant chunks from Ghana STG vector store."""

    def __init__(self, vector_store: ChromaVectorStore | None = None) -> None:
        self._store = vector_store or get_vector_store()
        self._top_k = settings.rag_top_k
        self._source_name = settings.ghana_guidelines_short_name
        self._document_name = settings.ghana_guidelines_display_name

    def retrieve(self, query: str, top_k: int | None = None) -> List[DocumentChunk]:
        """
        Retrieve top-K chunks for the query.
        Returns list of DocumentChunk with content and citation info.
        """
        k = top_k or self._top_k
        result = self._store.query(query_text=query, n_results=k)
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        ids = result.get("ids") or []
        chunks: List[DocumentChunk] = []
        for i, doc in enumerate(documents):
            meta = metadatas[i] if i < len(metadatas) else {}
            chunk_id = ids[i] if i < len(ids) else f"chunk_{i}"
            page = meta.get("page") if isinstance(meta.get("page"), int) else None
            chunks.append(
                DocumentChunk(
                    content=doc,
                    chunk_id=chunk_id,
                    page=page,
                    metadata={"source": self._source_name},
                )
            )
        return chunks

    def chunks_to_citations(self, chunks: List[DocumentChunk]) -> List[SourceCitation]:
        """Convert retrieved chunks to source citations (document name + page)."""
        return [
            SourceCitation(
                document_name=self._document_name,
                page=c.page,
            )
            for c in chunks
        ]
