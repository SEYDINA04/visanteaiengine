"""
Vector store - Adapter for Chroma (or similar) for RAG.

Stores and retrieves chunks from the Ghana Standard Treatment Guidelines.
Uses app core embeddings client.
"""

# Disable Chroma telemetry before import (avoids PostHog compatibility error)
import os
os.environ["ANONYMIZED_TELEMETRY"] = "false"

import logging
from pathlib import Path
from typing import List, Optional

import chromadb
# No-op Chroma telemetry to avoid posthog.capture() signature errors in some envs
try:
    from chromadb.telemetry.product.posthog import Posthog
    def _noop_capture(self, event): ...
    def _noop_direct(self, event): ...
    Posthog.capture = _noop_capture
    Posthog._direct_capture = _noop_direct
except Exception:
    pass

from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import settings
from app.core.embeddings import EmbeddingsClient, get_embeddings_client

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    Chroma-backed vector store for Ghana STG chunks.
    Uses async embedding client; Chroma API is sync so we embed then add/query.
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_client: Optional[EmbeddingsClient] = None,
    ) -> None:
        self._persist_dir = Path(persist_directory or settings.chroma_persist_directory).resolve()
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._collection_name = collection_name or settings.chroma_collection_name
        self._embedding_client = embedding_client or get_embeddings_client()
        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._ef,
            metadata={"source": "ghana_stg"},
        )

    def _get_embedding_fn(self):
        """Return embedding function compatible with Chroma (sync)."""
        return self._ef

    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
    ) -> None:
        """
        Add document chunks to the collection.
        Chroma's default embedding function will compute embeddings.
        """
        if metadatas is None:
            metadatas = [{}] * len(documents)
        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Added %d documents to collection %s", len(documents), self._collection_name)

    def add_documents_with_embeddings(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
    ) -> None:
        """Add documents with precomputed embeddings (e.g. from async Gemini)."""
        if metadatas is None:
            metadatas = [{}] * len(documents)
        self._collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """
        Query by text. Chroma uses its embedding function.
        Returns dict with keys: ids, documents, metadatas, distances.
        """
        result = self._collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return {
            "ids": result["ids"][0] if result["ids"] else [],
            "documents": result["documents"][0] if result["documents"] else [],
            "metadatas": result["metadatas"][0] if result["metadatas"] else [],
            "distances": result["distances"][0] if result.get("distances") else [],
        }

    def query_with_embeddings(
        self,
        query_embedding: List[float],
        n_results: int = 5,
    ) -> dict:
        """Query by precomputed embedding vector."""
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return {
            "ids": result["ids"][0] if result["ids"] else [],
            "documents": result["documents"][0] if result["documents"] else [],
            "metadatas": result["metadatas"][0] if result["metadatas"] else [],
            "distances": result["distances"][0] if result.get("distances") else [],
        }

    def count(self) -> int:
        """Return number of documents in collection."""
        return self._collection.count()

    def clear_collection(self) -> None:
        """Delete and recreate the collection. Use before re-indexing to avoid duplicate ID warnings."""
        self._client.delete_collection(name=self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._ef,
            metadata={"source": "ghana_stg"},
        )
        logger.info("Cleared collection %s", self._collection_name)


_vector_store: Optional[ChromaVectorStore] = None


def get_vector_store() -> ChromaVectorStore:
    """Return shared vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore()
    return _vector_store
