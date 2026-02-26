"""
Embeddings - Wrapper for creating text embeddings.

Uses Gemini text-embedding model for RAG vectorization.
Alternative: local sentence-transformers can be plugged in for offline use.
"""

import logging
from typing import List

from app.core.config import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    """
    Produces embedding vectors for RAG retrieval.
    Uses Google Gemini embedding model (text-embedding-004).
    """

    def __init__(self) -> None:
        api_key = settings.get_google_api_key()
        self._client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
        self._model = settings.gemini_embedding_model

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts. Returns list of vectors.
        Handles batching if API has limits.
        """
        if not texts:
            return []
        try:
            result = await self._client.aio.models.embed_content(
                model=f"models/{self._model}",
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=768,
                ),
            )
            if result and hasattr(result, "embeddings") and result.embeddings:
                return [e.values for e in result.embeddings]
            return []
        except Exception as e:
            logger.exception("Embed documents error: %s", e)
            return []

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query string. Returns one vector."""
        vectors = await self.embed_documents([query])
        return vectors[0] if vectors else []


_embeddings_client: EmbeddingsClient | None = None


def get_embeddings_client() -> EmbeddingsClient:
    """Return shared embeddings client."""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = EmbeddingsClient()
    return _embeddings_client
