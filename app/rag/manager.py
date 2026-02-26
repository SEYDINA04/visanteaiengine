"""
RAG Manager - Public API: fetch_evidence(), answer_with_sources().

Single entry point for the rest of the app to get Ghana STG–grounded answers.
Never mixed with triage decision scoring.
"""

import logging
from typing import List

from app.core.config import settings
from app.core.llm_engine import get_llm_engine
from app.rag.models import DocumentChunk, RAGResponse, SourceCitation
from app.rag.retriever import RAGRetriever
from app.rag.reranker import RAGReranker

logger = logging.getLogger(__name__)


class RAGManager:
    """
    Public RAG API. Retrieves from Ghana STG and optionally synthesizes answer with LLM.
    """

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        reranker: RAGReranker | None = None,
    ) -> None:
        self._retriever = retriever or RAGRetriever()
        self._reranker = reranker or RAGReranker()

    def fetch_evidence(self, query: str, top_k: int | None = None) -> List[DocumentChunk]:
        """
        Retrieve relevant chunks only (no LLM). Use for triage evidence display.
        """
        chunks = self._retriever.retrieve(query, top_k=top_k or settings.rag_top_k)
        return self._reranker.rerank(query, chunks, top_k=top_k or settings.rag_top_k)

    async def answer_with_sources(
        self,
        query: str,
        top_k: int | None = None,
        use_llm_synthesis: bool = True,
    ) -> RAGResponse:
        """
        Retrieve chunks and optionally synthesize an answer with LLM.
        Always includes source citations (document name + page) from Ghana STG.
        """
        chunks = self._retriever.retrieve(query, top_k=top_k or settings.rag_top_k)
        chunks = self._reranker.rerank(query, chunks, top_k=top_k or settings.rag_top_k)
        citations = self._retriever.chunks_to_citations(chunks)
        chunk_ids = [c.chunk_id for c in chunks]

        if not chunks:
            return RAGResponse(
                answer="No relevant guidelines were found for this query.",
                sources=[],
                chunk_ids=[],
                confidence=0.0,
            )

        if use_llm_synthesis:
            context = "\n\n".join(c.content for c in chunks)
            doc_name = settings.ghana_guidelines_display_name
            prompt = (
                f"Using ONLY the following excerpts from the document "
                f'"{doc_name}", answer the question. '
                f"If the excerpts do not contain enough information, say so. "
                f"Do not add information from outside the excerpts.\n\n"
                f"Excerpts:\n{context}\n\nQuestion: {query}\n\nAnswer:"
            )
            llm = get_llm_engine()
            answer = await llm.generate(
                prompt=prompt,
                system_instruction="You are a medical guidelines assistant. Answer only based on the provided excerpts. Be concise.",
                temperature=0.2,
                max_output_tokens=512,
            )
            if not answer:
                answer = chunks[0].content[:500] + "..."
            confidence = min(0.95, 0.5 + 0.1 * len(chunks))
        else:
            answer = chunks[0].content[:800]
            if len(chunks) > 1:
                answer += "\n\n[Additional relevant sections in guidelines.]"
            confidence = 0.7

        return RAGResponse(
            answer=answer,
            sources=citations,
            chunk_ids=chunk_ids,
            confidence=round(confidence, 2),
        )
