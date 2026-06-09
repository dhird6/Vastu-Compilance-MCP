"""GPT-4o structured layout planning from compliance report."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings
from app.models.schemas import LLMRoomAssignment, RoomOrientation, RuleEvaluationResult, UserLayoutConstraint

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore[misc, assignment]


class LayoutPlannerAI:
    """Uses LLM to assign target Vastu zones per room from report context."""

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

    def plan(
        self,
        *,
        orientations: list[RoomOrientation],
        rule_results: list[RuleEvaluationResult],
        locked_room_ids: set[str],
        constraints: list[UserLayoutConstraint],
    ) -> list[LLMRoomAssignment]:
        if not self._enabled:
            return self._deterministic_fallback(orientations, rule_results, locked_room_ids, constraints)

        payload = {
            "rooms": [
                {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "room_type": room.room_type,
                    "current_zone": room.zone,
                    "area_sqft": room.area,
                    "locked": room.room_id in locked_room_ids,
                }
                for room in orientations
            ],
            "violations": [
                {
                    "rule_id": result.rule_id,
                    "room_id": result.room_id,
                    "current_zone": result.zone,
                    "expected_zones": result.expected_zones,
                    "avoided_zones": result.avoided_zones,
                    "explanation": result.explanation,
                }
                for result in rule_results
                if not result.passed
            ],
            "constraints": [constraint.model_dump(mode="json") for constraint in constraints],
        }

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Vastu layout architect. Given rule violations, assign each "
                            "movable room to a target_zone that maximizes compliance. "
                            "Never change locked rooms. Return JSON: "
                            '{"assignments":[{"room_id":str,"target_zone":str,'
                            '"relative_position":{"radius_fraction":0.5}}]}'
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload)},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            assignments: list[LLMRoomAssignment] = []
            for item in parsed.get("assignments", []):
                room_id = str(item.get("room_id", ""))
                if not room_id or room_id in locked_room_ids:
                    continue
                assignments.append(
                    LLMRoomAssignment(
                        room_id=room_id,
                        target_zone=str(item.get("target_zone", "north")),
                        relative_position=dict(item.get("relative_position") or {}),
                    )
                )
            return assignments or self._deterministic_fallback(
                orientations, rule_results, locked_room_ids, constraints
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Layout planner LLM failed: %s", exc)
            return self._deterministic_fallback(orientations, rule_results, locked_room_ids, constraints)

    @staticmethod
    def _deterministic_fallback(
        orientations: list[RoomOrientation],
        rule_results: list[RuleEvaluationResult],
        locked_room_ids: set[str],
        constraints: list[UserLayoutConstraint],
    ) -> list[LLMRoomAssignment]:
        from app.services.correction.zone_placement_engine import resolve_target_zones_from_report

        zone_map = resolve_target_zones_from_report(orientations, rule_results)
        for constraint in constraints:
            if constraint.kind.value == "fixed_zone" and constraint.room_id and constraint.zone:
                zone_map[constraint.room_id] = constraint.zone

        assignments: list[LLMRoomAssignment] = []
        for room_id, target_zone in zone_map.items():
            if room_id in locked_room_ids:
                continue
            assignments.append(
                LLMRoomAssignment(
                    room_id=room_id,
                    target_zone=target_zone,
                    relative_position={"radius_fraction": 0.55},
                )
            )
        return assignments
