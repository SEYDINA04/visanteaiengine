"""
Risk analyzer - Deterministic risk flags and severity calculation.

Evaluates answers to detect emergency conditions and compute final severity/recommendation.
Does NOT use LLM; all logic is rule-based for consistency and auditability.
"""

import logging
import re
from typing import Any

from app.triage.models import QuestionId

logger = logging.getLogger(__name__)


# Keywords that indicate emergency (case-insensitive)
EMERGENCY_KEYWORDS = {
    QuestionId.BREATHING: ["yes", "difficulty", "can't breathe", "short of breath", "severe"],
    QuestionId.CHEST_PAIN: ["yes", "severe", "crushing", "pressure", "tight"],
    QuestionId.CONSCIOUSNESS: ["yes", "fainted", "passed out", "unconscious", "confusion"],
    QuestionId.BLEEDING: ["yes", "heavy", "severe", "lots of blood", "uncontrolled"],
}

# Pain scale 8-10 suggests higher acuity
HIGH_PAIN_THRESHOLD = 8

# Severity self-report mapping
SEVERITY_MAP = {"mild": 1, "moderate": 2, "severe": 3}


class RiskAnalyzer:
    """
    Deterministic risk and severity assessment.
    Used by state machine to decide emergency vs completed and to fill recommendation.
    """

    def _normalize(self, text: str) -> str:
        return (text or "").strip().lower()

    def _matches_keywords(self, answer: str, keywords: list[str]) -> bool:
        a = self._normalize(answer)
        return any(k in a for k in keywords)

    def check_emergency(
        self,
        question_id: str,
        answer: str,
        answers_so_far: dict[str, str],
    ) -> dict[str, Any] | None:
        """
        If current answer indicates emergency, return payload for emergency response.
        Otherwise return None.
        """
        try:
            qid = QuestionId(question_id)
        except ValueError:
            return None

        if qid == QuestionId.BREATHING and self._matches_keywords(
            answer, EMERGENCY_KEYWORDS[QuestionId.BREATHING]
        ):
            return {
                "severity_level": "critical",
                "recommendation": "Seek emergency care immediately. Difficulty breathing can be life-threatening.",
                "confidence_score": 0.92,
            }
        if qid == QuestionId.CHEST_PAIN and self._matches_keywords(
            answer, EMERGENCY_KEYWORDS[QuestionId.CHEST_PAIN]
        ):
            return {
                "severity_level": "critical",
                "recommendation": "Seek emergency care immediately. Chest pain may indicate a serious condition.",
                "confidence_score": 0.90,
            }
        if qid == QuestionId.CONSCIOUSNESS and self._matches_keywords(
            answer, EMERGENCY_KEYWORDS[QuestionId.CONSCIOUSNESS]
        ):
            return {
                "severity_level": "critical",
                "recommendation": "Seek emergency care immediately. Changes in consciousness require urgent evaluation.",
                "confidence_score": 0.91,
            }
        if qid == QuestionId.BLEEDING and self._matches_keywords(
            answer, EMERGENCY_KEYWORDS[QuestionId.BLEEDING]
        ):
            return {
                "severity_level": "critical",
                "recommendation": "Seek emergency care if bleeding is heavy or does not stop with pressure.",
                "confidence_score": 0.88,
            }

        # Pain level 9-10 with other risk factors could be escalated; for simplicity we don't auto-emergency on pain alone
        if qid == QuestionId.PAIN_LEVEL:
            match = re.search(r"\b([0-9]|10)\b", answer)
            if match:
                level = int(match.group(1))
                if level >= 9:
                    # Could optionally trigger emergency; here we allow flow to complete
                    pass

        return None

    def compute_final_assessment(self, answers: dict[str, str]) -> dict[str, Any]:
        """
        Compute severity_level, recommendation, and confidence_score when triage completes.
        Deterministic: based on severity self-report, pain, fever, etc.
        """
        severity_score = 0.0
        risk_flags: list[str] = []

        # Severity self-report
        severity_ans = self._normalize(answers.get(QuestionId.SEVERITY_SELF.value, ""))
        if "severe" in severity_ans:
            severity_score += 0.5
            risk_flags.append("Patient reported severe severity")
        elif "moderate" in severity_ans:
            severity_score += 0.25

        # Fever
        fever_ans = self._normalize(answers.get(QuestionId.FEVER.value, ""))
        if "yes" in fever_ans or "high" in fever_ans:
            severity_score += 0.15
            risk_flags.append("Fever reported")

        # Breathing (if not already emergency)
        breath_ans = self._normalize(answers.get(QuestionId.BREATHING.value, ""))
        if "yes" in breath_ans or "some" in breath_ans:
            severity_score += 0.2
            risk_flags.append("Breathing difficulty reported")

        # Pain level
        pain_ans = answers.get(QuestionId.PAIN_LEVEL.value, "")
        match = re.search(r"\b([0-9]|10)\b", pain_ans)
        if match:
            pain_level = int(match.group(1))
            if pain_level >= 7:
                severity_score += 0.2
                risk_flags.append(f"High pain level ({pain_level}/10)")
            elif pain_level >= 4:
                severity_score += 0.1

        # Cap and map to severity level
        severity_score = min(1.0, severity_score)
        if severity_score >= 0.6:
            severity_level = "high"
            recommendation = "Consider seeking care soon. Your symptoms suggest you should be evaluated by a healthcare provider."
        elif severity_score >= 0.35:
            severity_level = "moderate"
            recommendation = "You may benefit from a clinical evaluation. Consider visiting a clinic or speaking with a provider."
        else:
            severity_level = "low"
            recommendation = "Your symptoms appear mild. Rest and self-care may be sufficient. Seek care if symptoms worsen."

        confidence = 0.75 + (0.2 * min(len(answers) / 10.0, 1.0))
        confidence = min(0.95, confidence)

        return {
            "severity_level": severity_level,
            "recommendation": recommendation,
            "confidence_score": round(confidence, 2),
            "risk_flags": risk_flags,
        }
