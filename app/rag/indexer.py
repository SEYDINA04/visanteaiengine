"""
Indexer - Ingest Ghana Standard Treatment Guidelines PDF into the vector store.

Loads PDF (or text) from a configured path, chunks it, and adds to Chroma.
Run once (or on updates) to build the RAG index.
"""

import logging
from pathlib import Path
from typing import List, Optional

from app.core.config import settings
from app.core.vectorstore import ChromaVectorStore, get_vector_store
from app.rag.embeddings import chunk_document
from app.rag.models import DocumentChunk

logger = logging.getLogger(__name__)

# Project root (app/rag/indexer.py -> app -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"

# Default path for the Ghana STG document (resolved from project root)
DEFAULT_GUIDELINES_PATH = _DATA_DIR / "ghana_standard_treatment_guidelines_7ed_2017.pdf"
# Alternate name (e.g. if file was saved as "hana_..." by mistake)
ALTERNATE_PDF_NAMES = [
    "ghana_standard_treatment_guidelines_7ed_2017.pdf",
    "hana_standard_treatment_guidelines_7ed_2017.pdf",
    "standard_treatment_guidelines_7ed_2017.pdf",
]
DEFAULT_TEXT_PATH = _DATA_DIR / "ghana_stg_sample.txt"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from PDF. Requires pypdf or PyPDF2."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("Install pypdf or PyPDF2 for PDF ingestion: pip install pypdf")

    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _find_guidelines_pdf() -> Optional[Path]:
    """Resolve PDF path: explicit path, then default name, then alternates, then any PDF in data/."""
    if DEFAULT_GUIDELINES_PATH.exists():
        return DEFAULT_GUIDELINES_PATH
    for name in ALTERNATE_PDF_NAMES:
        candidate = _DATA_DIR / name
        if candidate.exists():
            return candidate
    # Fallback: any PDF in data/ (e.g. only one guidelines PDF)
    if _DATA_DIR.exists():
        for f in _DATA_DIR.glob("*.pdf"):
            return f
    return None


def load_guidelines_text(path: Optional[Path] = None) -> tuple[str, str]:
    """
    Load guidelines as text. If path is .pdf, extract text; else read as UTF-8.
    Returns (text, source_description) for logging.
    """
    p = path
    if p is None:
        p = _find_guidelines_pdf()
    if p is None or not p.exists():
        # Optional fallback: sample text when PDF is not available (e.g. CI or testing)
        sample = _DATA_DIR / "ghana_stg_sample.txt"
        if sample.exists():
            logger.info("Using sample guidelines file: %s", sample)
            return sample.read_text(encoding="utf-8"), str(sample)
        placeholder = (
            "Ghana Standard Treatment Guidelines 7th Edition 2017. "
            "Ministry of Health, Ghana National Drugs Programme. "
            "Fever: Assess for malaria in endemic areas. Paracetamol for fever. "
            "Respiratory: Upper respiratory tract infections are common. "
            "Cough: Consider antibiotics only if bacterial infection suspected. "
            "Pain: Use step-wise analgesia. Paracetamol first line. "
            "This is a placeholder. Add the full PDF to data/ and re-run indexer."
        )
        logger.warning(
            "No PDF found in %s (tried %s). Using placeholder text.",
            _DATA_DIR,
            ", ".join(ALTERNATE_PDF_NAMES),
        )
        return placeholder, "placeholder"
    if p.suffix.lower() == ".pdf":
        logger.info("Loading PDF: %s", p.resolve())
        return extract_text_from_pdf(p), str(p)
    logger.info("Loading text file: %s", p.resolve())
    return p.read_text(encoding="utf-8"), str(p)


def index_guidelines(
    guidelines_path: Optional[Path] = None,
    vector_store: Optional[ChromaVectorStore] = None,
    overwrite: bool = True,
) -> int:
    """
    Ingest Ghana STG into the vector store. Returns number of chunks indexed.
    If overwrite is True (default), clears the collection first so re-runs don't duplicate IDs.
    """
    store = vector_store or get_vector_store()
    text, source = load_guidelines_text(guidelines_path)
    if overwrite:
        store.clear_collection()
    chunks = chunk_document(
        text,
        source_name=settings.ghana_guidelines_short_name,
    )
    if not chunks:
        logger.warning("No chunks produced from guidelines text")
        return 0
    ids = [c.chunk_id for c in chunks]
    documents = [c.content for c in chunks]
    metadatas = [
        {"page": c.page, "source": settings.ghana_guidelines_short_name}
        for c in chunks
    ]
    store.add_documents(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Source: %s -> %d chunks", source, len(chunks))
    return len(chunks)
