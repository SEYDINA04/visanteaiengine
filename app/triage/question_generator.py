"""
Question generator - Generates next question text (optional LLM enhancement).

For MVP we use deterministic default questions from state_machine.
This module can later call LLM to personalize or localize question text.
"""

import logging
from typing import Optional

from app.core.llm_engine import get_llm_engine
from app.triage.models import QuestionId
from app.triage.state_machine import DEFAULT_QUESTIONS, TriageStateMachine

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """
    Returns question text for a given question_id.
    Default: use static text from state machine.
    Optional: use LLM to adapt text by language/context (not used for scoring).
    """

    def __init__(self, use_llm: bool = False) -> None:
        self._state_machine = TriageStateMachine()
        self._use_llm = use_llm
        self._llm = get_llm_engine() if use_llm else None

    def get_question_text(
        self,
        question_id: str,
        language: str = "en",
        context: Optional[dict] = None,
    ) -> str:
        """
        Return the question text. If use_llm and language != en, could call LLM to translate.
        For MVP we always return default English text.
        """
        try:
            qid = QuestionId(question_id)
            return DEFAULT_QUESTIONS.get(qid, f"Question: {question_id}")
        except ValueError:
            return f"Question: {question_id}"

    async def get_question_text_async(
        self,
        question_id: str,
        language: str = "en",
        context: Optional[dict] = None,
    ) -> str:
        """Async version for future LLM-based localization."""
        return self.get_question_text(question_id=question_id, language=language, context=context)
