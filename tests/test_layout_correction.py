"""Automated QA for layout auto-correction (Approach 1 + Approach 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.api.deps import get_pipeline
from app.api.deps_correction import get_ghost_engine, get_layout_generator
from app.core.config import get_settings
from app.models.schemas import (
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    GenerateGhostOverlayRequest,
    GenerateLayoutRequest,
    LayoutExportFormat,
    LLMRoomAssignment,
    Point2D,
    RuleEvaluationResult,
    RoomOrientation,
    Severity,
)
from app.services.correction.constraint_validator import LayoutConstraintValidator
from app.services.correction.dxf_exporter import export_layout_to_dxf_dict
from app.services.correction.transforms import (
    compute_plot_boundary,
    polygon_within_boundary,
    translate_polygon,
    zone_shift_vector,
)
from app.services.direction.engine import DirectionEngine
from app.services.geometry.engine import GeometryEngine
from app.services.rules.engine import VastuRuleEngine


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "config" / "schemas"


def _kitchen_south_payload() -> FloorPlanPayload:
    return FloorPlanPayload(
        source="direct_json",
        true_north_degrees=0,
        elements=[
            FloorPlanElement(
                id="r-kitchen",
                name="Kitchen",
                element_type=ElementType.room,
                polygon=[
                    Point2D(x=0, y=0),
                    Point2D(x=10, y=0),
                    Point2D(x=10, y=8),
                    Point2D(x=0, y=8),
                ],
                metadata={"room_type": "kitchen"},
            ),
        ],
    )


def _multi_room_payload() -> FloorPlanPayload:
    return FloorPlanPayload(
        source="direct_json",
        true_north_degrees=0,
        elements=[
            FloorPlanElement(
                id="r-kitchen",
                name="Kitchen",
                element_type=ElementType.room,
                polygon=[
                    Point2D(x=0, y=0),
                    Point2D(x=10, y=0),
                    Point2D(x=10, y=8),
                    Point2D(x=0, y=8),
                ],
                metadata={"room_type": "kitchen"},
            ),
            FloorPlanElement(
                id="r-master",
                name="Master Bedroom",
                element_type=ElementType.room,
                polygon=[
                    Point2D(x=12, y=0),
                    Point2D(x=28, y=0),
                    Point2D(x=28, y=12),
                    Point2D(x=12, y=12),
                ],
                metadata={"room_type": "master_bedroom"},
            ),
            FloorPlanElement(
                id="r-pooja",
                name="Pooja",
                element_type=ElementType.room,
                polygon=[
                    Point2D(x=0, y=10),
                    Point2D(x=8, y=10),
                    Point2D(x=8, y=18),
                    Point2D(x=0, y=18),
                ],
                metadata={"room_type": "pooja"},
            ),
        ],
    )


@pytest.fixture
def rule_engine() -> VastuRuleEngine:
    return VastuRuleEngine(get_settings().resolved_rules_path)


@pytest.fixture
def geometry_engine() -> GeometryEngine:
    return GeometryEngine()


@pytest.fixture
def direction_engine() -> DirectionEngine:
    return DirectionEngine()


# --- Approach 1: transforms + ghost overlay (6 tests) ---


def test_translate_polygon_preserves_vertex_count():
    polygon = [
        Point2D(x=0, y=0),
        Point2D(x=5, y=0),
        Point2D(x=5, y=5),
    ]
    moved = translate_polygon(polygon, dx=2.0, dy=3.0)
    assert len(moved) == 3
    assert moved[0].x == 2.0 and moved[0].y == 3.0
    assert moved[2].x == 7.0 and moved[2].y == 8.0


def test_zone_shift_vector_points_from_south_to_south_east():
    dx, dy = zone_shift_vector("south", "south_east")
    assert dx > 0
    assert dy > 0


def test_ghost_overlay_builds_corrections_for_kitchen_violation(
    rule_engine: VastuRuleEngine,
    geometry_engine: GeometryEngine,
    direction_engine: DirectionEngine,
):
    from app.services.correction.ghost_overlay import GhostOverlayEngine

    payload = _kitchen_south_payload()
    orientations = geometry_engine.build_room_orientations(
        payload, zone_resolver=direction_engine.resolve_zone
    )
    results = rule_engine.evaluate(orientations)
    failures = [result for result in results if not result.passed]
    assert failures, "Fixture kitchen must violate VR-001 (not in south_east)"

    engine = GhostOverlayEngine(geometry_engine, direction_engine)
    ghost = engine.build(payload, rule_results=failures, orientations=orientations)

    assert ghost.metadata.approach == "ghost_overlay"
    assert len(ghost.room_corrections) == 1
    correction = ghost.room_corrections[0]
    assert correction.room_id == "r-kitchen"
    assert correction.target_zone == "south_east"
    assert correction.translation["x"] != 0 or correction.translation["y"] != 0


def test_ghost_corrected_polygons_stay_within_plot_boundary(
    rule_engine: VastuRuleEngine,
    geometry_engine: GeometryEngine,
    direction_engine: DirectionEngine,
):
    from app.services.correction.ghost_overlay import GhostOverlayEngine

    payload = _multi_room_payload()
    orientations = geometry_engine.build_room_orientations(
        payload, zone_resolver=direction_engine.resolve_zone
    )
    failures = [result for result in rule_engine.evaluate(orientations) if not result.passed]

    ghost = GhostOverlayEngine(geometry_engine, direction_engine).build(
        payload, rule_results=failures, orientations=orientations
    )
    boundary = ghost.metadata.plot_boundary

    for correction in ghost.room_corrections:
        assert polygon_within_boundary(correction.corrected_polygon, boundary)


def test_ghost_overlay_includes_drawable_elements(
    rule_engine: VastuRuleEngine,
    geometry_engine: GeometryEngine,
    direction_engine: DirectionEngine,
):
    from app.services.correction.ghost_overlay import GhostOverlayEngine

    payload = _kitchen_south_payload()
    orientations = geometry_engine.build_room_orientations(
        payload, zone_resolver=direction_engine.resolve_zone
    )
    failures = [result for result in rule_engine.evaluate(orientations) if not result.passed]

    ghost = GhostOverlayEngine(geometry_engine, direction_engine).build(
        payload, rule_results=failures, orientations=orientations
    )
    kinds = {element.kind.value for element in ghost.elements}
    assert "room_polygon" in kinds
    assert "shift_arrow" in kinds
    assert "zone_compass" in kinds
    assert ghost.validation["rooms_within_boundary"] == len(ghost.room_corrections)


def test_ghost_overlay_json_schema_serializable(
    rule_engine: VastuRuleEngine,
    geometry_engine: GeometryEngine,
    direction_engine: DirectionEngine,
):
    from app.services.correction.ghost_overlay import GhostOverlayEngine

    payload = _kitchen_south_payload()
    orientations = geometry_engine.build_room_orientations(
        payload, zone_resolver=direction_engine.resolve_zone
    )
    failures = [result for result in rule_engine.evaluate(orientations) if not result.passed]
    ghost = GhostOverlayEngine(geometry_engine, direction_engine).build(
        payload, rule_results=failures, orientations=orientations
    )

    serialized = json.loads(ghost.model_dump_json())
    assert serialized["version"] == "1.0"
    assert "metadata" in serialized
    assert "elements" in serialized
    schema_path = SCHEMA_DIR / "ghost_geometry.schema.json"
    assert schema_path.exists()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["title"] == "GhostOverlayPayload"


# --- Approach 2: layout generator (6 tests) ---


def test_layout_generator_produces_all_rooms(rule_engine: VastuRuleEngine):
    payload = _multi_room_payload()
    engine = get_layout_generator()
    layout, _ = engine.generate(payload)

    assert len(layout.rooms) == 3
    room_ids = {room.room_id for room in layout.rooms}
    assert room_ids == {"r-kitchen", "r-master", "r-pooja"}


def test_layout_generator_improves_compliance_score(rule_engine: VastuRuleEngine):
    payload = _multi_room_payload()
    engine = get_layout_generator()
    layout, _ = engine.generate(payload)

    assert layout.metadata.generated_compliance_score >= layout.metadata.original_compliance_score


def test_layout_rooms_within_building_boundary(rule_engine: VastuRuleEngine):
    payload = _multi_room_payload()
    layout, _ = get_layout_generator().generate(payload)
    boundary = layout.metadata.plot_boundary

    for room in layout.rooms:
        assert polygon_within_boundary(room.polygon, boundary)


def test_layout_validator_flags_out_of_boundary_polygon(rule_engine: VastuRuleEngine):
    payload = _multi_room_payload()
    layout, _ = get_layout_generator().generate(payload)
    validator = LayoutConstraintValidator(rule_engine)

    layout.rooms[0].polygon = [
        Point2D(x=-50, y=-50),
        Point2D(x=-40, y=-50),
        Point2D(x=-40, y=-40),
        Point2D(x=-50, y=-40),
    ]
    result = validator.validate_generated_layout(layout, rule_engine=rule_engine)
    assert result["valid"] is False
    assert any(issue["code"] == "ROOM_OUT_OF_BOUNDARY" for issue in result["issues"])


def test_layout_llm_assignments_are_stitched(rule_engine: VastuRuleEngine):
    payload = _kitchen_south_payload()
    assignments = [
        LLMRoomAssignment(
            room_id="r-kitchen",
            target_zone="south_east",
            relative_position={"radius_fraction": 0.5},
        )
    ]
    layout, prompt = get_layout_generator().generate(payload, llm_assignments=assignments)

    assert layout.metadata.generation_strategy == "llm"
    assert layout.rooms[0].source == "llm"
    assert "violations" in prompt
    assert layout.rooms[0].zone in {"south_east", "east", "south"}


def test_dxf_export_blueprint_has_layers_and_entities(rule_engine: VastuRuleEngine):
    payload = _multi_room_payload()
    layout, _ = get_layout_generator().generate(
        payload, export_format=LayoutExportFormat.dxf
    )
    blueprint = export_layout_to_dxf_dict(layout)

    assert blueprint["format"] == "dxf_blueprint_v1"
    assert "VASTU_ROOMS" in blueprint["layers"]
    assert any(entity["layer"] == "VASTU_PLOT" for entity in blueprint["entities"])
    assert layout.export_artifacts.get("dxf") is not None


# --- Integration (2 tests) ---


@pytest.mark.asyncio
async def test_ghost_overlay_api_endpoint():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    payload = _kitchen_south_payload()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/correction/ghost-overlay",
            json=GenerateGhostOverlayRequest(payload=payload).model_dump(mode="json"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ghost_overlay"]["metadata"]["approach"] == "ghost_overlay"
    assert body["ghost_overlay"]["room_corrections"]


@pytest.mark.asyncio
async def test_generate_layout_api_endpoint():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    payload = _multi_room_payload()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/correction/generate-layout",
            json=GenerateLayoutRequest(payload=payload).model_dump(mode="json"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["layout"]["metadata"]["approach"] == "ai_layout_generator"
    assert len(body["layout"]["rooms"]) == 3
    assert "llm_prompt_context" in body


# --- Corrected 2D layout (same layout with suggestions applied) ---


def test_corrected_layout_applies_room_polygon_changes(rule_engine: VastuRuleEngine):
    from app.services.correction.corrected_layout import CorrectedLayoutBuilder
    from app.services.correction.ghost_overlay import GhostOverlayEngine

    payload = _kitchen_south_payload()
    geometry = GeometryEngine()
    direction = DirectionEngine()
    orientations = geometry.build_room_orientations(payload, zone_resolver=direction.resolve_zone)
    failures = [result for result in rule_engine.evaluate(orientations) if not result.passed]

    ghost = GhostOverlayEngine(geometry, direction).build(
        payload, rule_results=failures, orientations=orientations
    )
    result = CorrectedLayoutBuilder(
        geometry_engine=geometry,
        direction_engine=direction,
        rule_engine=rule_engine,
    ).build_from_ghost(payload, ghost, original_compliance_score=90.0)

    assert result.approach == "same_layout_with_suggestions"
    assert result.corrected_payload.source == "vastu_corrected_2d"
    assert len(result.changes_applied) == 1
    corrected_room = next(
        element for element in result.corrected_payload.elements if element.id == "r-kitchen"
    )
    original_room = next(element for element in payload.elements if element.id == "r-kitchen")
    assert corrected_room.polygon != original_room.polygon
    assert corrected_room.metadata.get("vastu_corrected") is True


@pytest.mark.asyncio
async def test_compliance_report_includes_corrected_layout():
    from app.api.deps import get_pipeline
    from app.models.schemas import AnalyzeComplianceRequest

    get_pipeline.cache_clear()
    request = AnalyzeComplianceRequest(payload=_kitchen_south_payload())
    report = await get_pipeline().run(request)

    assert report.corrected_layout is not None
    assert report.corrected_layout.corrected_payload.source == "vastu_corrected_2d"
    assert report.corrected_layout.corrected_compliance_score >= 0
    assert report.structured_output.get("corrected_layout") is not None


@pytest.mark.asyncio
async def test_apply_suggestions_api_endpoint():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    payload = _kitchen_south_payload()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/correction/apply-suggestions",
            json={"payload": payload.model_dump(mode="json")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["corrected_layout"]["approach"] == "same_layout_with_suggestions"
    assert body["corrected_layout"]["corrected_payload"]["source"] == "vastu_corrected_2d"
    assert len(body["corrected_layout"]["changes_applied"]) >= 1


def test_compute_plot_boundary_from_rooms():
    payload = _multi_room_payload()
    polygons = [element.polygon for element in payload.elements]
    boundary = compute_plot_boundary(polygons)
    assert len(boundary) >= 3
    assert all(isinstance(point, Point2D) for point in boundary)
