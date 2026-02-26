"""
Pydantic models for triage API request/response.

All triage endpoints use these structured models for validation and OpenAPI schema.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums and shared types
# -----------------------------------------------------------------------------


class QuestionId(str, Enum):
    """Canonical question IDs used in the triage flow."""

    CHIEF_COMPLAINT = "chief_complaint"
    DURATION = "duration"
    SEVERITY_SELF = "severity_self"
    FEVER = "fever"
    BREATHING = "breathing"
    CHEST_PAIN = "chest_pain"
    CONSCIOUSNESS = "consciousness"
    BLEEDING = "bleeding"
    PAIN_LEVEL = "pain_level"
    OTHER_SYMPTOMS = "other_symptoms"


class TriageState(str, Enum):
    """Current state of a triage session."""

    ONGOING = "ongoing"
    COMPLETED = "completed"
    EMERGENCY = "emergency"


class SeverityLevel(str, Enum):
    """Severity level from triage (deterministic)."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# -----------------------------------------------------------------------------
# Start triage
# -----------------------------------------------------------------------------


class TriageStartRequest(BaseModel):
    """Request body for POST /api/v1/triage/start."""

    patient_id: str | None = Field(default=None, description="Optional patient identifier")
    language: str = Field(default="en", description="Preferred language code")
    channel: str = Field(default="web", description="Channel: web, mobile, etc.")

    model_config = {
        "json_schema_extra": {
            "examples": [{"patient_id": None, "language": "en", "channel": "web"}]
        }
    }


class QuestionItem(BaseModel):
    """A single question in the triage flow."""

    question_id: str = Field(..., description="Unique question identifier")
    text: str = Field(..., description="Question text to display")


class TriageStartResponse(BaseModel):
    """Response from POST /api/v1/triage/start."""

    session_id: str = Field(..., description="UUID of the triage session")
    triage_state: Literal["ongoing"] = Field(default="ongoing", description="Initial state")
    first_question: QuestionItem = Field(..., description="First question to ask")


# -----------------------------------------------------------------------------
# Answer (continue triage)
# -----------------------------------------------------------------------------


class TriageAnswerRequest(BaseModel):
    """Request body for POST /api/v1/triage/answer."""

    session_id: str = Field(
        ...,
        description="UUID of the triage session (copy from POST /triage/start response)",
    )
    question_id: str = Field(
        ...,
        description="ID of the question being answered (e.g. chief_complaint for the first question)",
    )
    answer: str = Field(..., min_length=1, description="User's answer (non-empty)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "paste-session-id-from-start-response",
                    "question_id": "chief_complaint",
                    "answer": "I have a headache and fever",
                }
            ]
        }
    }


class TriageAnswerResponseOngoing(BaseModel):
    """Response when triage continues (next question)."""

    triage_state: Literal["ongoing"] = Field(default="ongoing")
    next_question: QuestionItem = Field(..., description="Next question to ask")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress 0.0–1.0")


class TriageAnswerResponseEmergency(BaseModel):
    """Response when triage determines emergency."""

    triage_state: Literal["emergency"] = Field(default="emergency")
    severity_level: Literal["critical"] = Field(default="critical")
    recommendation: str = Field(..., description="Immediate recommendation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0–1.0")


class TriageAnswerResponseCompleted(BaseModel):
    """Response when triage is completed (non-emergency)."""

    triage_state: Literal["completed"] = Field(default="completed")
    severity_level: Literal["low", "moderate", "high"] = Field(
        ..., description="Assessed severity"
    )
    recommendation: str = Field(..., description="Care recommendation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0–1.0")


# Union for answer response
TriageAnswerResponse = Union[
    TriageAnswerResponseOngoing,
    TriageAnswerResponseEmergency,
    TriageAnswerResponseCompleted,
]


# -----------------------------------------------------------------------------
# Result (report)
# -----------------------------------------------------------------------------


class TriageResultResponse(BaseModel):
    """Response from GET /api/v1/triage/result/{session_id}."""

    session_id: str = Field(..., description="UUID of the session")
    status: Literal["completed", "emergency"] = Field(
        ..., description="Final status of triage"
    )
    chief_complaint: str = Field(default="", description="Chief complaint summary")
    symptoms: list[str] = Field(default_factory=list, description="List of reported symptoms")
    risk_flags: list[str] = Field(default_factory=list, description="Identified risk flags")
    severity_level: str = Field(..., description="low, moderate, high, or critical")
    triage_category: str = Field(..., description="Triage category label")
    recommendation: str = Field(..., description="Care recommendation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0–1.0")
    created_at: datetime = Field(..., description="Session creation time")
