"""
Visanté AI Engine - Production-ready AI Triage Backend.

ASGI app entry for: uvicorn app.main:app

REST API under /api/v1:
- GET  /api/v1/status          Health check
- GET  /api/v1/test            Test endpoint
- GET  /api/v1/log             Recent logs
- POST /api/v1/triage/start   Start triage session
- POST /api/v1/triage/answer  Submit answer, get next question or result
- GET  /api/v1/triage/result/{session_id}  Get triage report

Clean architecture: api -> triage/rag -> core.
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import status, triage, rag
from app.core.config import settings
from app.core.log_buffer import BufferHandler

load_dotenv()

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("visante")
# Capture all logs for GET /api/v1/log (attach to root so every module is included)
_buffer_handler = BufferHandler()
_buffer_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
logging.getLogger().addHandler(_buffer_handler)


# -----------------------------------------------------------------------------
# Lifespan (startup/shutdown)
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure data dir exists. Shutdown: cleanup if needed."""
    from pathlib import Path
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
    logger.info("Visanté AI Engine started")
    yield
    logger.info("Visanté AI Engine shutting down")


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Visanté AI Engine",
    description="Production-ready AI Triage Backend. "
    "REST API for triage flow and optional RAG over Ghana Standard Treatment Guidelines (7th Ed., 2017).",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "System", "description": "Health and system endpoints"},
        {"name": "Triage", "description": "Triage session: start, answer, result"},
        {"name": "RAG - Guidelines", "description": "Query Ghana Standard Treatment Guidelines"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# API v1 routes
# -----------------------------------------------------------------------------
app.include_router(status.router, prefix="/api/v1")
app.include_router(triage.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")


# -----------------------------------------------------------------------------
# Root
# -----------------------------------------------------------------------------
@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    """Service info and links."""
    return {
        "service": settings.service_name,
        "version": settings.version,
        "docs": "/docs",
        "status": "/api/v1/status",
        "test": "/api/v1/test",
        "log": "/api/v1/log",
        "triage": "/api/v1/triage/start",
        "rag": "/api/v1/rag/query",
        "openapi": "/openapi.json",
    }
