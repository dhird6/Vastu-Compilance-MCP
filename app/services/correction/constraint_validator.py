"""Validate ghost overlays and generated layouts against physical + Vastu constraints."""

from __future__ import annotations

from app.models.schemas import (
    FloorPlanPayload,
    GeneratedLayoutDocument,
    GhostOverlayPayload,
    RoomOrientation,
    RuleEvaluationResult,
)
from app.services.correction.transforms import polygon_within_boundary
from app.services.geometry import shapely_ops
from app.services.rules.engine import VastuRuleEngine


class LayoutConstraintValidator:
    def __init__(self, rule_engine: VastuRuleEngine | None = None) -> None:
        self._rule_engine = rule_engine

    def validate_ghost_overlay(
        self,
        ghost: GhostOverlayPayload,
        *,
        rule_engine: VastuRuleEngine | None = None,
    ) -> dict[str, object]:
        engine = rule_engine or self._rule_engine
        boundary = ghost.metadata.plot_boundary
        issues: list[dict[str, str]] = []
        rooms_within = 0

        for correction in ghost.room_corrections:
            if polygon_within_boundary(correction.corrected_polygon, boundary):
                rooms_within += 1
            else:
                issues.append(
                    {
                        "code": "GHOST_OUT_OF_BOUNDARY",
                        "room_id": correction.room_id,
                        "message": "Corrected room polygon extends outside plot boundary.",
                    }
                )

        zone_improved = sum(1 for room in ghost.room_corrections if room.compliance_improved)
        vastu_ok = None
        if engine is not None:
            orientations = self._orientations_from_ghost(ghost)
            results = engine.evaluate(orientations)
            failed = [result for result in results if not result.passed]
            vastu_ok = len(failed) == 0

        return {
            "valid": len(issues) == 0,
            "rooms_within_boundary": rooms_within,
            "total_corrections": len(ghost.room_corrections),
            "zone_improvements": zone_improved,
            "vastu_compliant_after_correction": vastu_ok,
            "issues": issues,
        }

    def validate_generated_layout(
        self,
        layout: GeneratedLayoutDocument,
        *,
        rule_engine: VastuRuleEngine | None = None,
    ) -> dict[str, object]:
        engine = rule_engine or self._rule_engine
        boundary = layout.metadata.plot_boundary
        issues: list[dict[str, str]] = []

        for room in layout.rooms:
            if not polygon_within_boundary(room.polygon, boundary):
                issues.append(
                    {
                        "code": "ROOM_OUT_OF_BOUNDARY",
                        "room_id": room.room_id,
                        "message": f"Generated room '{room.room_name}' exceeds plot boundary.",
                    }
                )

        overlap_issues = self._detect_overlaps(layout)
        issues.extend(overlap_issues)

        vastu_ok = None
        failed_rules: list[RuleEvaluationResult] = []
        if engine is not None:
            orientations = [
                RoomOrientation(
                    room_id=room.room_id,
                    room_name=room.room_name,
                    room_type=room.room_type,
                    area=room.area,
                    centroid=room.centroid,
                    orientation_degrees=0.0,
                    zone=room.zone,
                    confidence=0.95,
                )
                for room in layout.rooms
            ]
            failed_rules = [result for result in engine.evaluate(orientations) if not result.passed]
            vastu_ok = len(failed_rules) == 0

        return {
            "valid": len(issues) == 0 and (vastu_ok is None or vastu_ok),
            "room_count": len(layout.rooms),
            "vastu_compliant": vastu_ok,
            "failed_rule_count": len(failed_rules),
            "target_score_met": layout.metadata.generated_compliance_score
            >= layout.metadata.original_compliance_score,
            "issues": issues,
        }

    def validate_corrected_payload(
        self,
        payload: FloorPlanPayload,
        orientations: list[RoomOrientation],
        *,
        rule_engine: VastuRuleEngine | None = None,
    ) -> dict[str, object]:
        engine = rule_engine or self._rule_engine
        from app.models.schemas import ElementType
        from app.services.correction.transforms import compute_plot_boundary, polygon_within_boundary

        room_polygons = [
            element.polygon
            for element in payload.elements
            if element.element_type == ElementType.room
        ]
        boundary = compute_plot_boundary(room_polygons)
        issues: list[dict[str, str]] = []

        for element in payload.elements:
            if element.element_type != ElementType.room or len(element.polygon) < 3:
                continue
            if not polygon_within_boundary(element.polygon, boundary):
                issues.append(
                    {
                        "code": "CORRECTED_ROOM_OUT_OF_BOUNDARY",
                        "room_id": element.id,
                        "message": f"Corrected room '{element.name}' exceeds plot boundary.",
                    }
                )

        vastu_ok = None
        failed_count = 0
        if engine is not None:
            failed_count = len([result for result in engine.evaluate(orientations) if not result.passed])
            vastu_ok = failed_count == 0

        return {
            "corrected_layout_valid": len(issues) == 0,
            "rooms_within_boundary": len(room_polygons) - len(issues),
            "vastu_compliant_after_apply": vastu_ok,
            "failed_rule_count_after_apply": failed_count,
            "issues": issues,
        }

    @staticmethod
    def _orientations_from_ghost(ghost: GhostOverlayPayload) -> list[RoomOrientation]:
        return [
            RoomOrientation(
                room_id=correction.room_id,
                room_name=correction.room_name,
                room_type=correction.room_type,
                area=shapely_ops.compute_area_centroid(correction.corrected_polygon)[0],
                centroid=correction.corrected_centroid,
                orientation_degrees=0.0,
                zone=correction.corrected_zone,
                confidence=0.9,
            )
            for correction in ghost.room_corrections
        ]

    @staticmethod
    def _detect_overlaps(layout: GeneratedLayoutDocument) -> list[dict[str, str]]:
        if not shapely_ops.SHAPELY_AVAILABLE:
            return []

        issues: list[dict[str, str]] = []
        shapes: list[tuple[str, object]] = []
        for room in layout.rooms:
            shape = shapely_ops.polygon_from_points(room.polygon)
            if shape is not None:
                shapes.append((room.room_id, shape))

        for index, (room_a, shape_a) in enumerate(shapes):
            for room_b, shape_b in shapes[index + 1 :]:
                intersection = shape_a.intersection(shape_b)
                if not intersection.is_empty and intersection.area > 0.5:
                    issues.append(
                        {
                            "code": "ROOM_OVERLAP",
                            "room_id": room_a,
                            "message": f"Room {room_a} overlaps {room_b}.",
                        }
                    )
        return issues
