from __future__ import annotations

from app.models.schemas import AIRecommendation, RoomOrientation, RuleEvaluationResult, Severity
from app.services.ai.openai_client import OpenAIService
from app.services.knowledge.vedic_knowledge import VedicKnowledgeService


class ExplainableAIEngine:
    """
    Rule-AI hybridization: deterministic rules decide pass/fail first.
    This layer explains failures and optionally enriches via OpenAI GPT-4o.
    """

    def __init__(
        self,
        knowledge_service: VedicKnowledgeService,
        openai_service: OpenAIService | None = None,
    ) -> None:
        self.knowledge_service = knowledge_service
        self.openai_service = openai_service or OpenAIService()

    def generate_recommendations(
        self,
        results: list[RuleEvaluationResult],
        room_orientations: list[RoomOrientation],
    ) -> list[AIRecommendation]:
        recommendations: list[AIRecommendation] = []
        room_map = {room.room_id: room for room in room_orientations}
        for result in results:
            if result.passed:
                continue
            room = room_map.get(result.room_id)
            references = (
                self.knowledge_service.get_references_for(room=room, is_failure=True)
                if room is not None
                else []
            )
            recommendations.append(
                AIRecommendation(
                    room_id=result.room_id,
                    recommendation=self._suggestion_for(result),
                    rationale=result.explanation,
                    confidence=min(0.95, result.confidence + 0.03),
                    severity=result.severity,
                    scriptural_references=references,
                )
            )
        return self.openai_service.enrich_recommendations(
            results, room_orientations, recommendations
        )

    def _suggestion_for(self, result: RuleEvaluationResult) -> str:
        if result.expected_zones:
            target = ", ".join(result.expected_zones)
            return f"Relocate or functionally swap this room toward {target} zone(s)."
        return "Re-evaluate room usage and alignment against rule constraints."

    def explanation_confidence(self, severity: Severity) -> float:
        mapping = {
            Severity.critical: 0.94,
            Severity.high: 0.91,
            Severity.medium: 0.88,
            Severity.low: 0.85,
            Severity.info: 0.80,
        }
        return mapping.get(severity, 0.80)
