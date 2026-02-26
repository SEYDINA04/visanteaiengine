"""
GET /api/v1/status - Health check endpoint.
GET /api/v1/test  - Simple test endpoint.
GET /api/v1/log    - Recent in-memory log entries.

Returns service name, status, and version for load balancers and monitoring.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.log_buffer import get_recent

router = APIRouter(tags=["System"])


@router.get(
    "/status",
    summary="Health check",
    description="Returns service name, status, and version. Use for load balancer health checks and monitoring.",
)
async def get_status() -> dict:
    """Health check: service name, status, and version."""
    return {
        "service": settings.service_name,
        "status": "online",
        "version": settings.version,
    }


@router.get(
    "/test",
    summary="Test endpoint",
    description="Simple test endpoint for smoke tests or connectivity checks.",
)
async def get_test() -> dict:
    """Returns OK and service info."""
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.version,
    }


@router.get(
    "/log",
    summary="Recent logs",
    description="Returns the most recent in-memory log entries (newest last).",
)
async def get_log(
    limit: int = Query(default=100, ge=1, le=500, description="Max number of entries to return"),
) -> dict:
    """Return recent log entries from the in-memory buffer."""
    entries = get_recent(limit=limit)
    # Convert epoch timestamp to ISO for readability
    for e in entries:
        ts = e.get("timestamp")
        if isinstance(ts, (int, float)):
            e["timestamp"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return {"count": len(entries), "logs": entries}
