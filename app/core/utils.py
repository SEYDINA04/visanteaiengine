"""
Utility functions: chunking, normalization, and helpers.

Used by RAG indexer and across the application.
"""

import re
from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
    separators: List[str] | None = None,
) -> List[str]:
    """
    Split text into overlapping chunks for RAG.
    Tries to break on paragraph or sentence boundaries when possible.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " "]
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Try to break at a separator
        segment = text[start:end]
        break_at = -1
        for sep in separators:
            idx = segment.rfind(sep)
            if idx > chunk_size // 2:
                break_at = idx + len(sep)
                break
        if break_at > 0:
            chunk = text[start : start + break_at].strip()
            start += break_at - overlap
        else:
            chunk = segment.strip()
            start = end - overlap
        if chunk:
            chunks.append(chunk)
    return chunks


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines to single space."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def safe_str(value: str | None, default: str = "") -> str:
    """Return string or default if None/empty."""
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default
