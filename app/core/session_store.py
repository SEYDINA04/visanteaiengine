"""
In-memory session store for triage (MVP).

Maps session_id -> session data. Replace with Redis/DB in production.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# In-memory store: session_id (str) -> dict
_sessions: dict[str, dict[str, Any]] = {}


def create_session(
    patient_id: str | None = None,
    language: str = "en",
    channel: str = "web",
) -> str:
    """Create a new triage session. Returns session_id (UUID string)."""
    session_id = str(uuid4())
    _sessions[session_id] = {
        "session_id": session_id,
        "patient_id": patient_id,
        "language": language,
        "channel": channel,
        "triage_state": "ongoing",
        "answers": {},
        "chief_complaint": "",
        "symptoms": [],
        "risk_flags": [],
        "severity_level": None,
        "triage_category": "",
        "recommendation": "",
        "confidence_score": None,
        "created_at": datetime.now(timezone.utc),
    }
    return session_id


def get_session(session_id: str) -> dict[str, Any] | None:
    """Return session data or None if not found."""
    return _sessions.get(session_id)


def update_session(session_id: str, updates: dict[str, Any]) -> bool:
    """Update session with given keys. Returns False if session not found."""
    if session_id not in _sessions:
        return False
    _sessions[session_id].update(updates)
    return True


def session_exists(session_id: str) -> bool:
    """Check if session exists."""
    return session_id in _sessions
