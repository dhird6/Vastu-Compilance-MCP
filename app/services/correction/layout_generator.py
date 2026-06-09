"""Approach 2: AI Layout Generator — new-instance compliant floor plan."""

from __future__ import annotations

from uuid import uuid4

from app.models.schemas import (
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    GeneratedLayoutDocument,
    GeneratedLayoutMetadata,
    GeneratedRoomPlacement,
    LayoutExportFormat,
    LLMRoomAssignment,
    Point2D,
    RoomOrientation,
    RuleEvaluationResult,
)
from app.services.correction.constraint_validator import LayoutConstraintValidator
from app.services.correction.transforms import (
    compute_plot_boundary,
    ensure_polygon_in_boundary,
    polygon_centroid,
    rectangle_for_area,
    zone_target_point,
)
from app.services.direction.engine import DirectionEngine
from app.services.geometry import shapely_ops
from app.services.geometry.engine import GeometryEngine
from app.services.rules.engine import VastuRuleEngine
from app.services.scoring.compliance import ComplianceScoringEngine


class LayoutGeneratorEngine:
    """
    Generates a new layout document from original constraints.

    Pipeline:
    1. Parse spatial logic (plot boundary, room areas/types, adjacency hints)
    2. Build LLM prompt context (or accept structured LLM assignments)
    3. Deterministically place rooms in preferred Vastu zones
    4. Validate + export as JSON / DXF artifact descriptors
    """

    def __init__(
        self,
        geometry_engine: GeometryEngine | None = None,
        direction_engine: DirectionEngine | None = None,
        rule_engine: VastuRuleEngine | None = None,
        scoring_engine: ComplianceScoringEngine | None = None,
        validator: LayoutConstraintValidator | None = None,
    ) -> None:
        self._geometry = geometry_engine or GeometryEngine()
        self._direction = direction_engine or DirectionEngine()
        self._rule_engine = rule_engine
        self._scoring = scoring_engine or ComplianceScoringEngine()
        self._validator = validator or LayoutConstraintValidator(rule_engine)

    def build_llm_prompt_context(
        self,
        payload: FloorPlanPayload,
        orientations: list[RoomOrientation],
        rule_results: list[RuleEvaluationResult],
    ) -> dict[str, object]:
        room_polygons = [
            element.polygon
            for element in payload.elements
            if element.element_type == ElementType.room
        ]
        plot_center = shapely_ops.compute_plot_center(room_polygons)
        plot_boundary = compute_plot_boundary(room_polygons)
        failures = [result for result in rule_results if not result.passed]

        return {
            "instruction": (
                "Assign each room to a Vastu zone that satisfies YAML rules. "
                "Return JSON array of {room_id, target_zone, relative_position}."
            ),
            "true_north_degrees": payload.true_north_degrees,
            "plot_center": plot_center.model_dump(),
            "plot_boundary": [point.model_dump() for point in plot_boundary],
            "rooms": [
                {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "room_type": room.room_type,
                    "area_sqft": room.area,
                    "current_zone": room.zone,
                    "preferred_zones": self._preferred_zones(room.room_type),
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
                }
                for result in failures
            ],
            "vastu_zones": self._direction.build_directional_zones(),
        }

    def generate(
        self,
        payload: FloorPlanPayload,
        *,
        orientations: list[RoomOrientation] | None = None,
        rule_results: list[RuleEvaluationResult] | None = None,
        llm_assignments: list[LLMRoomAssignment] | None = None,
        export_format: LayoutExportFormat = LayoutExportFormat.vastu_layout_json,
        target_compliance_score: float = 100.0,
        source_request_id: str | None = None,
    ) -> tuple[GeneratedLayoutDocument, dict[str, object]]:
        orientations = orientations or self._geometry.build_room_orientations(
            payload, zone_resolver=self._direction.resolve_zone
        )
        rule_results = rule_results or (
            self._rule_engine.evaluate(orientations) if self._rule_engine else []
        )

        room_polygons = [
            element.polygon
            for element in payload.elements
            if element.element_type == ElementType.room
        ]
        plot_center = shapely_ops.compute_plot_center(room_polygons)
        plot_radius = shapely_ops.compute_plot_radius(room_polygons, plot_center)
        plot_boundary = compute_plot_boundary(room_polygons)

        original_summary = self._scoring.compute_summary(len(orientations), rule_results)
        assignment_map = {item.room_id: item for item in (llm_assignments or [])}
        strategy = "llm" if llm_assignments else "deterministic"

        placements: list[GeneratedRoomPlacement] = []
        for room in orientations:
            assignment = assignment_map.get(room.room_id)
            target_zone = (
                assignment.target_zone
                if assignment
                else self._resolve_target_zone(room, rule_results)
            )
            center = zone_target_point(
                plot_center,
                target_zone,
                plot_radius=plot_radius,
                radius_fraction=self._radius_fraction(assignment),
            )
            polygon = rectangle_for_area(center, max(room.area, 1.0))
            polygon = ensure_polygon_in_boundary(polygon, plot_boundary, plot_center)
            centroid = polygon_centroid(polygon)
            zone = self._direction.resolve_zone(
                shapely_ops.bearing_from_center(
                    centroid, plot_center, payload.true_north_degrees
                )
            )
            area, _ = shapely_ops.compute_area_centroid(polygon)
            placements.append(
                GeneratedRoomPlacement(
                    room_id=room.room_id,
                    room_name=room.room_name,
                    room_type=room.room_type,
                    polygon=polygon,
                    area=area,
                    centroid=centroid,
                    zone=zone,
                    source="llm" if assignment else "deterministic",
                )
            )

        generated_results = (
            self._rule_engine.evaluate(self._placements_to_orientations(placements))
            if self._rule_engine
            else []
        )
        generated_summary = self._scoring.compute_summary(
            len(placements), generated_results
        )

        layout = GeneratedLayoutDocument(
            metadata=GeneratedLayoutMetadata(
                true_north_degrees=payload.true_north_degrees,
                plot_center=plot_center,
                plot_boundary=plot_boundary,
                original_compliance_score=original_summary.compliance_score,
                generated_compliance_score=generated_summary.compliance_score,
                source_request_id=source_request_id or str(uuid4()),
                generation_strategy=strategy,
            ),
            rooms=placements,
            walls=self._synthetic_walls(placements),
        )
        layout.validation = self._validator.validate_generated_layout(
            layout, rule_engine=self._rule_engine
        )
        layout.export_artifacts = self._build_export_artifacts(layout, export_format)

        prompt_context = self.build_llm_prompt_context(payload, orientations, rule_results)
        return layout, prompt_context

    def _resolve_target_zone(
        self,
        room: RoomOrientation,
        rule_results: list[RuleEvaluationResult],
    ) -> str:
        for result in rule_results:
            if result.room_id == room.room_id and not result.passed and result.expected_zones:
                return result.expected_zones[0]
        preferred = self._preferred_zones(room.room_type)
        return preferred[0] if preferred else room.zone

    @staticmethod
    def _preferred_zones(room_type: str) -> list[str]:
        from app.domain.vastu_zones import VastuZoneCatalog

        for zone in VastuZoneCatalog.ZONES:
            if room_type in zone.recommended_uses:
                return [zone.key]
        return ["north"]

    @staticmethod
    def _radius_fraction(assignment: LLMRoomAssignment | None) -> float:
        if assignment is None or not assignment.relative_position:
            return 0.55
        offset = assignment.relative_position.get("radius_fraction", 0.55)
        return max(0.25, min(0.75, float(offset)))

    @staticmethod
    def _placements_to_orientations(
        placements: list[GeneratedRoomPlacement],
    ) -> list[RoomOrientation]:
        return [
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
            for room in placements
        ]

    @staticmethod
    def _synthetic_walls(placements: list[GeneratedRoomPlacement]) -> list[FloorPlanElement]:
        walls: list[FloorPlanElement] = []
        for room in placements:
            for index in range(len(room.polygon)):
                start = room.polygon[index]
                end = room.polygon[(index + 1) % len(room.polygon)]
                walls.append(
                    FloorPlanElement(
                        id=f"wall-{room.room_id}-{index}",
                        name=f"Wall {room.room_name} segment {index}",
                        element_type=ElementType.wall,
                        polygon=[start, end],
                        metadata={"room_id": room.room_id, "synthetic": True},
                    )
                )
        return walls

    @staticmethod
    def _build_export_artifacts(
        layout: GeneratedLayoutDocument,
        export_format: LayoutExportFormat,
    ) -> dict[str, object]:
        json_payload = layout.model_dump(mode="json")
        artifacts: dict[str, object] = {
            "vastu_layout_json": json_payload,
            "filename_hint": f"vastu_layout_{layout.metadata.source_request_id}.json",
        }
        if export_format == LayoutExportFormat.dxf:
            from app.services.correction.dxf_exporter import export_layout_to_dxf_dict

            artifacts["dxf"] = export_layout_to_dxf_dict(layout)
            artifacts["filename_hint"] = (
                f"vastu_layout_{layout.metadata.source_request_id}.dxf"
            )
        return artifacts
