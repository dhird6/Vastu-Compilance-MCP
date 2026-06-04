from __future__ import annotations

import math

from app.models.schemas import (
    AIRecommendation,
    RemediationAction,
    RemediationActionType,
    RemediationPlan,
    RoomOrientation,
    RuleEvaluationResult,
)
from app.services.direction.engine import DirectionEngine


class RemediationPlanner:
    """Builds machine-readable remediation plans from rule failures (Phases 2–4)."""

    def __init__(self, direction_engine: DirectionEngine | None = None) -> None:
        self._direction = direction_engine or DirectionEngine()

    def build_plan(
        self,
        results: list[RuleEvaluationResult],
        orientations: list[RoomOrientation],
        recommendations: list[AIRecommendation],
    ) -> RemediationPlan:
        room_map = {room.room_id: room for room in orientations}
        rec_map = {rec.room_id: rec for rec in recommendations}
        actions: list[RemediationAction] = []

        for result in results:
            if result.passed:
                continue

            room = room_map.get(result.room_id)
            target_zone = result.expected_zones[0] if result.expected_zones else None
            rec = rec_map.get(result.room_id)

            actions.append(
                RemediationAction(
                    action_id=f"{result.rule_id}-{result.room_id}-highlight",
                    room_id=result.room_id,
                    rule_id=result.rule_id,
                    action_type=RemediationActionType.highlight_room,
                    description=f"Highlight non-compliant room for rule {result.rule_id}",
                    parameters={
                        "severity": result.severity.value,
                        "color_hint": _severity_color(result.severity.value),
                    },
                    requires_user_approval=False,
                    auto_applicable=True,
                    confidence=result.confidence,
                )
            )

            actions.append(
                RemediationAction(
                    action_id=f"{result.rule_id}-{result.room_id}-params",
                    room_id=result.room_id,
                    rule_id=result.rule_id,
                    action_type=RemediationActionType.set_parameter,
                    description="Set Vastu tracking parameters on room",
                    parameters={
                        "VastuCompliant": False,
                        "VastuZone": result.zone,
                        "VastuTargetZone": target_zone or "",
                        "VastuRuleId": result.rule_id,
                    },
                    requires_user_approval=False,
                    auto_applicable=True,
                    confidence=result.confidence,
                )
            )

            if target_zone and room is not None:
                shift = _zone_shift_hint(result.zone, target_zone)
                distance_feet = 3.0
                translation = {
                    "x": round(shift["dx"] * distance_feet, 4),
                    "y": round(shift["dy"] * distance_feet, 4),
                    "z": 0.0,
                }
                target_point = {
                    "x": round(room.centroid.x + translation["x"], 4),
                    "y": round(room.centroid.y + translation["y"], 4),
                }

                actions.append(
                    RemediationAction(
                        action_id=f"{result.rule_id}-{result.room_id}-guide",
                        room_id=result.room_id,
                        rule_id=result.rule_id,
                        action_type=RemediationActionType.draw_zone_guide,
                        description=f"Draw alignment guide toward {target_zone}",
                        parameters={
                            "current_zone": result.zone,
                            "target_zone": target_zone,
                            "centroid": {"x": room.centroid.x, "y": room.centroid.y},
                            "target_point": target_point,
                            "guide_length_feet": distance_feet,
                            "shift_vector": shift,
                        },
                        requires_user_approval=False,
                        auto_applicable=True,
                        confidence=min(0.9, result.confidence),
                    )
                )

                actions.append(
                    RemediationAction(
                        action_id=f"{result.rule_id}-{result.room_id}-ghost",
                        room_id=result.room_id,
                        rule_id=result.rule_id,
                        action_type=RemediationActionType.show_ghost_design,
                        description=(
                            f"Ghost preview: proposed room position toward {target_zone} "
                            f"({distance_feet:.1f} ft shift)"
                        ),
                        parameters={
                            "current_zone": result.zone,
                            "target_zone": target_zone,
                            "centroid": {"x": room.centroid.x, "y": room.centroid.y},
                            "target_point": target_point,
                            "shift_vector": shift,
                            "shift_distance_feet": distance_feet,
                            "translation_feet": translation,
                            "ghost_style": "cyan_dashed",
                            "room_type": room.room_type,
                        },
                        requires_user_approval=False,
                        auto_applicable=True,
                        confidence=min(0.88, result.confidence),
                    )
                )

                actions.append(
                    RemediationAction(
                        action_id=f"{result.rule_id}-{result.room_id}-move",
                        room_id=result.room_id,
                        rule_id=result.rule_id,
                        action_type=RemediationActionType.move_room_boundaries,
                        description=(
                            f"Move room boundary walls {distance_feet:.1f} ft toward {target_zone}"
                        ),
                        parameters={
                            "current_zone": result.zone,
                            "target_zone": target_zone,
                            "centroid": {"x": room.centroid.x, "y": room.centroid.y},
                            "target_point": target_point,
                            "shift_vector": shift,
                            "shift_distance_feet": distance_feet,
                            "translation_feet": translation,
                        },
                        requires_user_approval=True,
                        auto_applicable=False,
                        confidence=min(0.85, result.confidence),
                    )
                )

            if rec is not None and target_zone:
                actions.append(
                    RemediationAction(
                        action_id=f"{result.rule_id}-{result.room_id}-annotate",
                        room_id=result.room_id,
                        rule_id=result.rule_id,
                        action_type=RemediationActionType.annotate,
                        description=rec.recommendation,
                        parameters={
                            "annotation_text": rec.recommendation,
                            "rationale": rec.rationale,
                            "scriptural_references": rec.scriptural_references,
                        },
                        requires_user_approval=False,
                        auto_applicable=True,
                        confidence=rec.confidence,
                    )
                )

        auto_count = sum(1 for action in actions if action.auto_applicable)
        manual_count = len(actions) - auto_count
        ghost_count = sum(
            1 for action in actions if action.action_type == RemediationActionType.show_ghost_design
        )
        summary = (
            f"{len(results)} violation(s) → {len(actions)} action(s) "
            f"({auto_count} auto, {manual_count} need approval, {ghost_count} ghost preview)"
        )

        return RemediationPlan(
            actions=actions,
            summary=summary,
            auto_applicable_count=auto_count,
            manual_approval_count=manual_count,
        )


def _severity_color(severity: str) -> str:
    return {
        "critical": "#FF0000",
        "high": "#FF6600",
        "medium": "#FFAA00",
        "low": "#FFFF00",
        "info": "#00AAFF",
    }.get(severity, "#FF6600")


def _zone_mid_angle(zone: str) -> float:
    mapping = {
        "north": 0.0,
        "north_east": 45.0,
        "east": 90.0,
        "south_east": 135.0,
        "south": 180.0,
        "south_west": 225.0,
        "west": 270.0,
        "north_west": 315.0,
    }
    return mapping.get(zone, 0.0)


def _zone_unit_vector(zone: str) -> tuple[float, float]:
    """Compass unit vector: North=0° → (dx=0, dy=1) in plan coordinates."""
    angle_rad = math.radians(_zone_mid_angle(zone))
    return round(math.sin(angle_rad), 4), round(math.cos(angle_rad), 4)


def _zone_shift_hint(current_zone: str, target_zone: str) -> dict[str, float]:
    """Unit vector from current zone toward target zone (plan XY, Y=north)."""
    cx, cy = _zone_unit_vector(current_zone)
    tx, ty = _zone_unit_vector(target_zone)
    dx, dy = tx - cx, ty - cy
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return {"dx": 0.0, "dy": 0.0}
    return {"dx": round(dx / length, 4), "dy": round(dy / length, 4)}
