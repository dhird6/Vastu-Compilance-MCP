"""Stateless thin MCP tool handlers — modular JSON in/out."""

from __future__ import annotations

from app.domain.vastu_zones import VastuZoneCatalog
from app.models.schemas import EvaluateRoomRequest, ResolveZoneRequest
from app.services.compliance_pipeline import CompliancePipeline
from app.services.geometry.engine import GeometryEngine


class ThinMCPTools:
    """Element-level tools expecting Revit Element IDs, polygons, and room params."""

    def __init__(self, pipeline: CompliancePipeline) -> None:
        self.pipeline = pipeline
        self.geometry = pipeline.geometry_engine

    def evaluate_room(self, request: EvaluateRoomRequest) -> dict:
        orientation = self.geometry.evaluate_single_room(
            element_id=request.element_id,
            room_name=request.room_name,
            room_type=request.room_type,
            polygon=request.polygon,
            true_north_degrees=request.true_north_degrees,
            all_room_polygons=request.all_room_polygons,
        )
        rule_results = self.pipeline.rule_engine.evaluate_room(orientation)
        return {
            "orientation": orientation.model_dump(mode="json"),
            "rule_results": [r.model_dump(mode="json") for r in rule_results],
            "passed": all(r.passed for r in rule_results) if rule_results else True,
        }

    def resolve_zone(self, request: ResolveZoneRequest) -> dict:
        bearing = (request.bearing_degrees + request.true_north_degrees) % 360.0
        zone_key = VastuZoneCatalog.resolve(bearing)
        zone = VastuZoneCatalog.get(zone_key)
        return {
            "zone": zone_key,
            "sanskrit": zone.sanskrit if zone else "",
            "element": zone.element if zone else "",
            "bearing_degrees": bearing,
        }

    def check_brahmasthan(self, request: EvaluateRoomRequest) -> dict:
        orientation = self.geometry.evaluate_single_room(
            element_id=request.element_id,
            room_name=request.room_name,
            room_type=request.room_type,
            polygon=request.polygon,
            true_north_degrees=request.true_north_degrees,
            all_room_polygons=request.all_room_polygons,
        )
        in_brahm = bool(orientation.metadata.get("in_brahmasthan", False))
        heavy = orientation.room_type in {"kitchen", "toilet", "staircase", "storage"}
        return {
            "element_id": request.element_id,
            "in_brahmasthan": in_brahm,
            "room_type": orientation.room_type,
            "violation": in_brahm and heavy,
            "message": (
                "Heavy room overlaps Brahmasthan — keep center open."
                if in_brahm and heavy
                else "No Brahmasthan violation detected."
            ),
        }
