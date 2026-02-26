"""
Application configuration.

Centralizes environment variables, API keys, and vector DB connection settings.
Uses Pydantic Settings for validation and type safety.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Service
    # -------------------------------------------------------------------------
    service_name: str = Field(default="Visanté AI Engine", description="Service display name")
    version: str = Field(default="1.0.0", description="API version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug logging")

    # -------------------------------------------------------------------------
    # LLM (Gemini)
    # -------------------------------------------------------------------------
    google_api_key: str = Field(default="", description="Google AI / Gemini API key")
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model for question generation and RAG synthesis",
    )
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        description="Model used for embedding text (RAG)",
    )

    @model_validator(mode="after")
    def use_gemini_key_if_set(self):
        """Allow GEMINI_API_KEY when GOOGLE_API_KEY is not set."""
        if not (self.google_api_key or "").strip():
            alt = (os.getenv("GEMINI_API_KEY") or "").strip()
            if alt:
                object.__setattr__(self, "google_api_key", alt)
        return self

    # -------------------------------------------------------------------------
    # Vector store (Chroma)
    # -------------------------------------------------------------------------
    chroma_persist_directory: str = Field(
        default="./data/chroma",
        description="Directory for Chroma persistence",
    )
    chroma_collection_name: str = Field(
        default="ghana_standard_treatment_guidelines",
        description="Chroma collection for Ghana STG documents",
    )
    rag_top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve for RAG")
    rag_chunk_size: int = Field(default=800, ge=200, le=2000, description="Character size per chunk")
    rag_chunk_overlap: int = Field(default=100, ge=0, le=400, description="Overlap between chunks")

    # -------------------------------------------------------------------------
    # RAG source document
    # -------------------------------------------------------------------------
    ghana_guidelines_display_name: str = Field(
        default="Republic of Ghana, Ministry of Health, Ghana National Drugs Programme (GNDP), "
        "Standard Treatment Guidelines, 7th Edition, 2017",
        description="Official document name for source citations",
    )
    ghana_guidelines_short_name: str = Field(
        default="Ghana STG 7th Ed. 2017",
        description="Short name for citations",
    )

    @property
    def chroma_path(self) -> Path:
        """Resolved path for Chroma persistence."""
        return Path(self.chroma_persist_directory).resolve()

    def get_google_api_key(self) -> str:
        """Return non-empty API key or raise."""
        key = self.google_api_key or ""
        key = key.strip()
        if not key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY is required. "
                "Set it in .env or environment. Get a key: https://aistudio.google.com/apikey"
            )
        return key


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (load .env once)."""
    return Settings()


# Convenience alias
settings = get_settings()
