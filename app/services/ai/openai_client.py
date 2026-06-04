"""OpenAI GPT-4o integration — structured outputs; never overrides rule pass/fail."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings
from app.models.schemas import (
    AIRecommendation,
    ComplianceChatRequest,
    ComplianceChatResponse,
    ComplianceReport,
    RoomOrientation,
    RuleEvaluationResult,
)

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore[misc, assignment]


class OpenAIService:
    """
    Rule-AI hybridization layer.

    Deterministic VastuRuleEngine always decides pass/fail first.
    OpenAI only enriches explanations and chat when OPENAI_API_KEY is set.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.openai_api_key) and OPENAI_AVAILABLE
        self._model = settings.openai_model
        self._client: Any = None
        if self._enabled:
            self._client = OpenAI(api_key=settings.openai_api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enrich_recommendations(
        self,
        results: list[RuleEvaluationResult],
        orientations: list[RoomOrientation],
        base_recommendations: list[AIRecommendation],
    ) -> list[AIRecommendation]:
        if not self._enabled or not base_recommendations:
            return base_recommendations

        failed = [r for r in results if not r.passed]
        if not failed:
            return base_recommendations

        room_map = {o.room_id: o for o in orientations}
        payload = {
            "failed_rules": [r.model_dump(mode="json") for r in failed[:8]],
            "rooms": [
                {
                    "room_id": o.room_id,
                    "room_type": o.room_type,
                    "zone": o.zone,
                    "area": o.area,
                    "in_brahmasthan": o.metadata.get("in_brahmasthan", False),
                }
                for o in orientations
                if o.room_id in {f.room_id for f in failed}
            ],
        }

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Vastu compliance advisor for AEC/BIM. "
                            "Rules have ALREADY been evaluated deterministically — do NOT change pass/fail. "
                            "Return JSON: {\"recommendations\": [{\"room_id\": str, \"recommendation\": str, "
                            "\"rationale\": str, \"confidence\": float}]}. "
                            "Explain WHY each rule failed and HOW to fix parametrically in Revit."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload)},
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            ai_items = parsed.get("recommendations", [])
            enriched: list[AIRecommendation] = []
            base_map = {r.room_id: r for r in base_recommendations}
            for item in ai_items:
                room_id = str(item.get("room_id", ""))
                base = base_map.get(room_id)
                if base is None:
                    continue
                enriched.append(
                    AIRecommendation(
                        room_id=room_id,
                        recommendation=str(item.get("recommendation", base.recommendation)),
                        rationale=str(item.get("rationale", base.rationale)),
                        confidence=min(0.98, float(item.get("confidence", base.confidence))),
                        severity=base.severity,
                        scriptural_references=base.scriptural_references,
                    )
                )
            seen = {r.room_id for r in enriched}
            for base in base_recommendations:
                if base.room_id not in seen:
                    enriched.append(base)
            return enriched or base_recommendations
        except Exception as exc:  # noqa: BLE001 — fallback to deterministic
            logger.warning("OpenAI enrichment failed, using template: %s", exc)
            return base_recommendations

    def chat(
        self,
        request: ComplianceChatRequest,
        report: ComplianceReport | None,
        template_reply: ComplianceChatResponse,
    ) -> ComplianceChatResponse:
        if not self._enabled or report is None:
            return template_reply

        context = {
            "score": report.summary.compliance_score,
            "grade": report.summary.grade,
            "failed_rules": [r.model_dump(mode="json") for r in report.rule_results if not r.passed][:10],
            "remediation_summary": report.remediation_plan.summary,
        }
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Vastu compliance chat for Revit users. "
                            "Pass/fail is fixed by deterministic engine — never contradict rule results. "
                            "Return JSON: {\"reply\": str, \"cited_rule_ids\": [str]}."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"question": request.message, "report": context}),
                    },
                ],
                temperature=0.4,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            return ComplianceChatResponse(
                reply=str(parsed.get("reply", template_reply.reply)),
                cited_rule_ids=[str(r) for r in parsed.get("cited_rule_ids", template_reply.cited_rule_ids)],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI chat failed, using template: %s", exc)
            return template_reply
