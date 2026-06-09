"""Approach 1: Ghost Overlay System — non-destructive corrected geometry package."""

from __future__ import annotations

from uuid import uuid4

from app.models.schemas import (
    ElementType,
    FloorPlanPayload,
    GhostElementKind,
    GhostGeometryElement,
    GhostOverlayMetadata,
    GhostOverlayPayload,
    GhostRenderStyle,
    GhostRoomCorrection,
    Point2D,
    RoomOrientation,
    RuleEvaluationResult,
)
from app.services.correction.constraint_validator import LayoutConstraintValidator
from app.services.correction.transforms import (
    clip_polygon_to_boundary,
    compute_plot_boundary,
    ensure_polygon_in_boundary,
    polygon_centroid,
    translation_to_target,
    translate_polygon,
    zone_shift_vector,
    zone_target_point,
)
from app.services.direction.engine import DirectionEngine
from app.services.geometry import shapely_ops
from app.services.geometry.engine import GeometryEngine


class GhostOverlayEngine:
    """
    Builds a GhostOverlayPayload from floor plan + rule failures.

    The CAD plugin renders `elements` as detail curves / overlay graphics
    without modifying source Revit/DWG geometry.
    """

    def __init__(
        self,
        geometry_engine: GeometryEngine | None = None,
        direction_engine: DirectionEngine | None = None,
        validator: LayoutConstraintValidator | None = None,
    ) -> None:
        self._geometry = geometry_engine or GeometryEngine()
        self._direction = direction_engine or DirectionEngine()
        self._validator = validator or LayoutConstraintValidator()

    def build(
        self,
        payload: FloorPlanPayload,
        *,
        rule_results: list[RuleEvaluationResult],
        orientations: list[RoomOrientation] | None = None,
        shift_distance_feet: float = 3.0,
        source_request_id: str | None = None,
    ) -> GhostOverlayPayload:
        orientations = orientations or self._geometry.build_room_orientations(
            payload, zone_resolver=self._direction.resolve_zone
        )
        room_map = {room.room_id: room for room in orientations}
        polygon_map = {
            element.id: element.polygon
            for element in payload.elements
            if element.element_type == ElementType.room
        }

        room_polygons = list(polygon_map.values())
        plot_center = shapely_ops.compute_plot_center(room_polygons)
        plot_radius = shapely_ops.compute_plot_radius(room_polygons, plot_center)
        plot_boundary = compute_plot_boundary(room_polygons)

        failures_by_room: dict[str, list[RuleEvaluationResult]] = {}
        for result in rule_results:
            if result.passed:
                continue
            failures_by_room.setdefault(result.room_id, []).append(result)

        corrections: list[GhostRoomCorrection] = []
        elements: list[GhostGeometryElement] = []

        for room_id, failures in failures_by_room.items():
            room = room_map.get(room_id)
            original_polygon = polygon_map.get(room_id)
            if room is None or original_polygon is None:
                continue

            target_zone = failures[0].expected_zones[0] if failures[0].expected_zones else None
            if not target_zone:
                continue

            shift_dx, shift_dy = zone_shift_vector(room.zone, target_zone)
            translation = {
                "x": round(shift_dx * shift_distance_feet, 4),
                "y": round(shift_dy * shift_distance_feet, 4),
                "z": 0.0,
            }

            target_point = zone_target_point(
                plot_center, target_zone, plot_radius=plot_radius
            )
            full_dx, full_dy = translation_to_target(
                room.centroid,
                target_point,
                max_distance=shift_distance_feet,
            )
            if abs(full_dx) > abs(translation["x"]) or abs(full_dy) > abs(translation["y"]):
                translation = {"x": full_dx, "y": full_dy, "z": 0.0}

            corrected_polygon = translate_polygon(
                original_polygon, translation["x"], translation["y"]
            )
            corrected_polygon = ensure_polygon_in_boundary(
                corrected_polygon, plot_boundary, plot_center
            )
            corrected_centroid = polygon_centroid(corrected_polygon)
            corrected_zone = self._direction.resolve_zone(
                shapely_ops.bearing_from_center(
                    corrected_centroid,
                    plot_center,
                    payload.true_north_degrees,
                )
            )

            preferred = {target_zone}
            compliance_improved = corrected_zone in preferred or corrected_zone != room.zone

            correction = GhostRoomCorrection(
                room_id=room_id,
                room_name=room.room_name,
                room_type=room.room_type,
                original_polygon=original_polygon,
                corrected_polygon=corrected_polygon,
                original_centroid=room.centroid,
                corrected_centroid=corrected_centroid,
                original_zone=room.zone,
                target_zone=target_zone,
                corrected_zone=corrected_zone,
                translation=translation,
                rule_ids=[failure.rule_id for failure in failures],
                compliance_improved=compliance_improved,
            )
            corrections.append(correction)

            elements.extend(self._elements_for_correction(correction, failures[0].rule_id))

        elements.extend(self._compass_elements(plot_center, plot_radius))

        ghost = GhostOverlayPayload(
            metadata=GhostOverlayMetadata(
                true_north_degrees=payload.true_north_degrees,
                plot_center=plot_center,
                plot_boundary=plot_boundary,
                source_request_id=source_request_id or str(uuid4()),
            ),
            room_corrections=corrections,
            elements=elements,
        )
        ghost.validation = self._validator.validate_ghost_overlay(ghost)
        return ghost

    def _elements_for_correction(
        self,
        correction: GhostRoomCorrection,
        rule_id: str,
    ) -> list[GhostGeometryElement]:
        coords = [{"x": p.x, "y": p.y} for p in correction.corrected_polygon]
        original_coords = [{"x": p.x, "y": p.y} for p in correction.original_polygon]

        return [
            GhostGeometryElement(
                element_id=f"ghost-room-{correction.room_id}",
                kind=GhostElementKind.room_polygon,
                room_id=correction.room_id,
                rule_id=rule_id,
                geometry={
                    "type": "Polygon",
                    "coordinates": [coords],
                    "original_coordinates": [original_coords],
                },
                style=GhostRenderStyle.cyan_dashed,
                metadata={
                    "room_name": correction.room_name,
                    "target_zone": correction.target_zone,
                    "translation": correction.translation,
                },
            ),
            GhostGeometryElement(
                element_id=f"ghost-arrow-{correction.room_id}",
                kind=GhostElementKind.shift_arrow,
                room_id=correction.room_id,
                rule_id=rule_id,
                geometry={
                    "type": "LineString",
                    "coordinates": [
                        {
                            "x": correction.original_centroid.x,
                            "y": correction.original_centroid.y,
                        },
                        {
                            "x": correction.corrected_centroid.x,
                            "y": correction.corrected_centroid.y,
                        },
                    ],
                },
                style=GhostRenderStyle.gold_solid,
                z_index=20,
            ),
            GhostGeometryElement(
                element_id=f"ghost-label-{correction.room_id}",
                kind=GhostElementKind.label,
                room_id=correction.room_id,
                rule_id=rule_id,
                geometry={
                    "type": "Point",
                    "coordinates": {
                        "x": correction.corrected_centroid.x,
                        "y": correction.corrected_centroid.y,
                    },
                    "text": f"{correction.room_name} → {correction.target_zone.replace('_', ' ')}",
                },
                style=GhostRenderStyle.cyan_dashed,
                z_index=30,
            ),
        ]

    def _compass_elements(
        self,
        plot_center: Point2D,
        plot_radius: float,
    ) -> list[GhostGeometryElement]:
        radius = max(plot_radius * 0.35, 4.0)
        spokes: list[dict[str, float]] = []
        for angle in (0, 45, 90, 135, 180, 225, 270, 315):
            import math

            rad = math.radians(angle)
            spokes.append(
                {
                    "x": round(plot_center.x + math.sin(rad) * radius, 4),
                    "y": round(plot_center.y + math.cos(rad) * radius, 4),
                }
            )

        return [
            GhostGeometryElement(
                element_id="ghost-compass",
                kind=GhostElementKind.zone_compass,
                geometry={
                    "type": "CompassRose",
                    "center": {"x": plot_center.x, "y": plot_center.y},
                    "radius_feet": radius,
                    "spokes": spokes,
                },
                style=GhostRenderStyle.blue_thin,
                z_index=5,
            )
        ]
