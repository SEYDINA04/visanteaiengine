"""
LLM Engine - Wrapper for AI model calls.

Uses Google Gemini for:
- Triage question generation (assist only; triage decisions are deterministic)
- RAG answer synthesis from retrieved Ghana STG chunks

Never used for final risk classification or triage scoring.
"""

import logging
from typing import Any

from app.core.config import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Async wrapper for Gemini API.
    Used for question generation and RAG synthesis only.
    """

    def __init__(self) -> None:
        api_key = settings.get_google_api_key()
        self._client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
        self._model = settings.gemini_model

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
    ) -> str:
        """
        Generate text from the LLM (async).
        Returns the generated text or empty string on failure.
        """
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                system_instruction=system_instruction or "",
            )
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text.strip()
            return ""
        except Exception as e:
            logger.exception("LLM generate error: %s", e)
            return ""

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any] | None:
        """
        Generate JSON object from the LLM.
        Expects prompt to ask for valid JSON; returns parsed dict or None.
        """
        import json
        text = await self.generate(
            prompt=prompt,
            system_instruction=(system_instruction or "") + "\nRespond with valid JSON only, no markdown.",
            temperature=temperature,
            max_output_tokens=2048,
        )
        if not text:
            return None
        # Strip markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("LLM JSON parse error: %s", e)
            return None


# Singleton for dependency injection
_llm_engine: LLMEngine | None = None


def get_llm_engine() -> LLMEngine:
    """Return shared LLM engine instance."""
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine
