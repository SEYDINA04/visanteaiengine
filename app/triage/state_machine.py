"""
Triage state machine - Deterministic triage logic.

Defines the flow of questions and transitions. Risk classification is computed
by risk_analyzer from answers; this module only decides next question or terminal state.
No LLM is used for state transitions or final severity.
"""

import logging
from typing import Any

from app.triage.models import TriageState, QuestionId
from app.triage.risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)

# Ordered flow: after each question we either go to next or terminate
QUESTION_FLOW = [
    QuestionId.CHIEF_COMPLAINT,
    QuestionId.DURATION,
    QuestionId.SEVERITY_SELF,
    QuestionId.FEVER,
    QuestionId.BREATHING,
    QuestionId.CHEST_PAIN,
    QuestionId.CONSCIOUSNESS,
    QuestionId.BLEEDING,
    QuestionId.PAIN_LEVEL,
    QuestionId.OTHER_SYMPTOMS,
]

# Default question text (can be overridden by question_generator for i18n/LLM)
DEFAULT_QUESTIONS: dict[QuestionId, str] = {
    QuestionId.CHIEF_COMPLAINT: "What is your main reason for seeking care today?",
    QuestionId.DURATION: "How long have you had these symptoms?",
    QuestionId.SEVERITY_SELF: "How would you rate the severity: mild, moderate, or severe?",
    QuestionId.FEVER: "Do you have a fever or have you felt hot recently?",
    QuestionId.BREATHING: "Are you having any difficulty breathing?",
    QuestionId.CHEST_PAIN: "Do you have chest pain or pressure?",
    QuestionId.CONSCIOUSNESS: "Have you had any fainting, confusion, or loss of consciousness?",
    QuestionId.BLEEDING: "Are you experiencing any significant bleeding?",
    QuestionId.PAIN_LEVEL: "On a scale of 1 to 10, how would you rate your pain?",
    QuestionId.OTHER_SYMPTOMS: "Are there any other symptoms we should know about?",
}


class TriageStateMachine:
    """
    Deterministic state machine for triage.
    - Tracks current question index and answers.
    - Delegates risk evaluation to RiskAnalyzer.
    - Returns next question or terminal state (completed/emergency).
    """

    def __init__(self) -> None:
        self._risk_analyzer = RiskAnalyzer()

    def get_first_question_id(self) -> str:
        """Return the first question ID in the flow."""
        return QUESTION_FLOW[0].value

    def get_question_text(self, question_id: str) -> str:
        """Return default question text for a question ID."""
        try:
            qid = QuestionId(question_id)
            return DEFAULT_QUESTIONS.get(qid, f"Question: {question_id}")
        except ValueError:
            return f"Question: {question_id}"

    def get_next_question_id(self, current_index: int) -> str | None:
        """
        Return the next question ID in the flow, or None if we have finished.
        current_index is 0-based index of the question just answered.
        """
        next_index = current_index + 1
        if next_index >= len(QUESTION_FLOW):
            return None
        return QUESTION_FLOW[next_index].value

    def get_question_index(self, question_id: str) -> int | None:
        """Return 0-based index of question_id in flow, or None if not found."""
        try:
            qid = QuestionId(question_id)
            return QUESTION_FLOW.index(qid)
        except (ValueError, ValueError):
            return None

    def progress(self, answered_count: int) -> float:
        """Return progress as float in [0.0, 1.0]."""
        total = len(QUESTION_FLOW)
        if total <= 0:
            return 1.0
        return min(1.0, answered_count / total)

    def process_answer(
        self,
        question_id: str,
        answer: str,
        answers_so_far: dict[str, str],
    ) -> tuple[TriageState, dict[str, Any] | None]:
        """
        Process one answer in context of previous answers.
        Returns (new_state, payload).
        - If ongoing: payload has next_question_id, next_question_text, progress.
        - If emergency/completed: payload has severity_level, recommendation, confidence_score.
        """
        current_index = self.get_question_index(question_id)
        if current_index is None:
            logger.warning("Unknown question_id %s, treating as end of flow", question_id)
            current_index = len(QUESTION_FLOW) - 1

        # Merge answer into history
        new_answers = {**answers_so_far, question_id: answer}

        # Check for emergency (deterministic rules)
        emergency_result = self._risk_analyzer.check_emergency(question_id, answer, new_answers)
        if emergency_result is not None:
            return TriageState.EMERGENCY, emergency_result

        # Check if we have more questions
        next_id = self.get_next_question_id(current_index)
        if next_id is None:
            # End of flow: compute final severity and recommendation (deterministic)
            completed_result = self._risk_analyzer.compute_final_assessment(new_answers)
            return TriageState.COMPLETED, completed_result

        return TriageState.ONGOING, {
            "next_question_id": next_id,
            "next_question_text": self.get_question_text(next_id),
            "progress": self.progress(current_index + 1),
        }
