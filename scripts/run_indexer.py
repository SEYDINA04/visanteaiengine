"""
Run RAG indexer: ingest Ghana Standard Treatment Guidelines into the vector store.

Usage (from project root):
    python -m scripts.run_indexer

Place the PDF at data/ghana_standard_treatment_guidelines_7ed_2017.pdf
or use the sample at data/ghana_stg_sample.txt for testing.
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import logging
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.indexer import index_guidelines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    n = index_guidelines()
    logger.info("Indexed %d chunks.", n)


if __name__ == "__main__":
    main()
