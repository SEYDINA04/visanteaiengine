"""
Reranker - Optional reranker for better precision of retrieved chunks.

MVP: no-op (return chunks as-is). Can be extended with cross-encoder or LLM-based reranking.
"""

import logging
from typing import List

from app.rag.models import DocumentChunk

logger = logging.getLogger(__name__)


class RAGReranker:
    """Optional reranker. Default implementation returns chunks unchanged."""

    def rerank(self, query: str, chunks: List[DocumentChunk], top_k: int = 5) -> List[DocumentChunk]:
        """
        Rerank chunks by relevance to query. Default: return first top_k as-is.
        Override to add cross-encoder or other reranking.
        """
        return chunks[:top_k]
