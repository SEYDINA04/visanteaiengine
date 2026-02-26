"""
Chunk embedding logic for RAG.

Uses core chunking (utils) and core vectorstore; this module encapsulates
RAG-specific embedding behavior (e.g. chunk size from config, metadata for citations).
"""

import logging
from typing import List

from app.core.config import settings
from app.core.utils import chunk_text
from app.rag.models import DocumentChunk

logger = logging.getLogger(__name__)


def chunk_document(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
    source_name: str | None = None,
    base_page: int = 1,
) -> List[DocumentChunk]:
    """
    Split document text into chunks with metadata for RAG.
    Returns list of DocumentChunk with content and optional page.
    """
    cs = chunk_size or settings.rag_chunk_size
    ov = overlap or settings.rag_chunk_overlap
    chunks_raw = chunk_text(text, chunk_size=cs, overlap=ov)
    result: List[DocumentChunk] = []
    for i, content in enumerate(chunks_raw):
        result.append(
            DocumentChunk(
                content=content,
                chunk_id=f"{source_name or 'doc'}_chunk_{i}",
                page=base_page if chunks_raw else None,
                metadata={"source": source_name or "Ghana STG 7th Ed. 2017"},
            )
        )
    return result
