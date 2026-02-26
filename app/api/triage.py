"""
Triage API: start, answer, result.

REST endpoints for the triage flow. Business logic lives in app.triage.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.session_store import (
    create_session,
    get_session,
    update_session,
    session_exists,
)
from app.triage.models import (
    TriageStartRequest,
    TriageStartResponse,
    TriageAnswerRequest,
    TriageAnswerResponseOngoing,
    TriageAnswerResponseEmergency,
    TriageAnswerResponseCompleted,
    TriageResultResponse,
    QuestionItem,
)
from app.triage.state_machine import TriageStateMachine
from app.triage.models import TriageState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triage", tags=["Triage"])

_state_machine = TriageStateMachine()


@router.post(
    "/start",
    response_model=TriageStartResponse,
    summary="Start triage session",
    description="Starts a new triage session and returns the first question to ask the patient.",
)
async def triage_start(request: TriageStartRequest) -> TriageStartResponse:
    """Start a triage session; returns session_id and first_question."""
    session_id = create_session(
        patient_id=request.patient_id,
        language=request.language,
        channel=request.channel,
    )
    first_qid = _state_machine.get_first_question_id()
    first_text = _state_machine.get_question_text(first_qid)
    return TriageStartResponse(
        session_id=session_id,
        triage_state="ongoing",
        first_question=QuestionItem(question_id=first_qid, text=first_text),
    )


@router.post(
    "/answer",
    summary="Submit answer and continue triage",
    description="Submit an answer to the current question. Returns next question (ongoing), "
    "emergency recommendation, or completed triage result. "
    "Use the session_id returned from POST /triage/start. "
    "Use the question_id from the current question (first is chief_complaint).",
)
async def triage_answer(request: TriageAnswerRequest):
    """
    Process answer: validate session, run state machine, return next question or terminal state.
    """
    if not session_exists(request.session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found. Use the session_id returned from POST /triage/start.",
        )
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Use the session_id returned from POST /triage/start.",
        )
    if session.get("triage_state") != "ongoing":
        raise HTTPException(
            status_code=400,
            detail=f"Triage already ended with state: {session.get('triage_state')}",
        )

    state, payload = _state_machine.process_answer(
        question_id=request.question_id,
        answer=request.answer,
        answers_so_far=session.get("answers") or {},
    )

    if state == TriageState.ONGOING and payload:
        update_session(request.session_id, {
            "answers": {**(session.get("answers") or {}), request.question_id: request.answer},
        })
        if request.question_id == "chief_complaint":
            update_session(request.session_id, {"chief_complaint": request.answer[:500]})
        return TriageAnswerResponseOngoing(
            triage_state="ongoing",
            next_question=QuestionItem(
                question_id=payload["next_question_id"],
                text=payload["next_question_text"],
            ),
            progress=payload["progress"],
        )

    if state == TriageState.EMERGENCY and payload:
        update_session(request.session_id, {
            "triage_state": "emergency",
            "answers": {**(session.get("answers") or {}), request.question_id: request.answer},
            "severity_level": payload.get("severity_level", "critical"),
            "recommendation": payload.get("recommendation", ""),
            "confidence_score": payload.get("confidence_score", 0.9),
            "risk_flags": session.get("risk_flags", []) + ["Emergency criteria met"],
            "triage_category": "emergency",
        })
        return TriageAnswerResponseEmergency(
            triage_state="emergency",
            severity_level="critical",
            recommendation=payload.get("recommendation", "Seek emergency care."),
            confidence_score=payload.get("confidence_score", 0.9),
        )

    if state == TriageState.COMPLETED and payload:
        answers = {**(session.get("answers") or {}), request.question_id: request.answer}
        update_session(request.session_id, {
            "triage_state": "completed",
            "answers": answers,
            "severity_level": payload.get("severity_level", "low"),
            "recommendation": payload.get("recommendation", ""),
            "confidence_score": payload.get("confidence_score", 0.8),
            "risk_flags": payload.get("risk_flags", []),
            "triage_category": payload.get("severity_level", "low"),
        })
        return TriageAnswerResponseCompleted(
            triage_state="completed",
            severity_level=payload["severity_level"],
            recommendation=payload["recommendation"],
            confidence_score=payload["confidence_score"],
        )

    # Fallback: treat as completed with low severity
    update_session(request.session_id, {
        "triage_state": "completed",
        "answers": {**(session.get("answers") or {}), request.question_id: request.answer},
        "severity_level": "low",
        "recommendation": "Please consult a healthcare provider if symptoms persist.",
        "confidence_score": 0.7,
        "triage_category": "low",
    })
    return TriageAnswerResponseCompleted(
        triage_state="completed",
        severity_level="low",
        recommendation="Please consult a healthcare provider if symptoms persist.",
        confidence_score=0.7,
    )


@router.get(
    "/result/{session_id}",
    response_model=TriageResultResponse,
    summary="Get triage result",
    description="Returns the structured triage report for a completed or emergency session.",
)
async def triage_result(session_id: str) -> TriageResultResponse:
    """Return full triage report for a session."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    state = session.get("triage_state")
    if state not in ("completed", "emergency"):
        raise HTTPException(
            status_code=400,
            detail=f"Triage not yet complete. Current state: {state}",
        )
    return TriageResultResponse(
        session_id=session_id,
        status=state,
        chief_complaint=session.get("chief_complaint") or "",
        symptoms=list(session.get("answers", {}).values()) or [],
        risk_flags=session.get("risk_flags") or [],
        severity_level=session.get("severity_level") or "low",
        triage_category=session.get("triage_category") or state,
        recommendation=session.get("recommendation") or "",
        confidence_score=session.get("confidence_score") or 0.0,
        created_at=session.get("created_at") or datetime.utcnow(),
    )
