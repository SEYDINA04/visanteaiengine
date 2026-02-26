"""
Visanté AI Engine - Production-ready AI Triage Backend.

Clean architecture:
- api: REST endpoints (triage, status)
- core: config, LLM, embeddings, vectorstore, utils
- triage: state machine, risk analysis, question generation
- rag: Ghana Standard Treatment Guidelines retrieval
"""

__version__ = "1.0.0"
