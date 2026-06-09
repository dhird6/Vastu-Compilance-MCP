"""Tests for report-driven new 2D layout generation + CAD I/O."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_pipeline
from app.api.deps_layout import get_report_layout_generator
from app.main import app
from app.models.schemas import (
    AnalyzeComplianceRequest,
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    GenerateLayoutFromReportRequest,
    MCPToolCallRequest,
    Point2D,
    UserLayoutConstraint,
    UserConstraintKind,
)
from app.mcp.server import MCPServer
from app.services.correction.dxf_exporter import layout_to_dxf_bytes
from app.services.correction.transforms import compute_plot_boundary
from app.services.correction.zone_placement_engine import (
    ZonePlacementEngine,
    resolve_target_zones_from_report,
)
from app.services.geometry import shapely_ops


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
                id="r-bedroom",
                name="Master Bedroom",
                element_type=ElementType.room,
                polygon=[
                    Point2D(x=12, y=0),
                    Point2D(x=22, y=0),
                    Point2D(x=22, y=10),
                    Point2D(x=12, y=10),
                ],
                metadata={"room_type": "master_bedroom"},
            ),
            FloorPlanElement(
                id="r-toilet",
                name="Toilet",
                element_type=ElementType.room,
                polygon=[
                    Point2D(x=0, y=10),
                    Point2D(x=6, y=10),
                    Point2D(x=6, y=14),
                    Point2D(x=0, y=14),
                ],
                metadata={"room_type": "toilet"},
            ),
        ],
    )


@pytest.fixture
def generator():
    return get_report_layout_generator()


@pytest.mark.asyncio
async def test_generate_layout_from_report_improves_score(generator):
    payload = _multi_room_payload()
    result = await generator.generate(
        GenerateLayoutFromReportRequest(
            payload=payload,
            use_llm_planner=False,
            generate_svg_preview=False,
        )
    )

    assert result.layout.rooms
    assert result.layout.metadata.generated_compliance_score >= result.layout.metadata.original_compliance_score
    assert result.io_bundle.revit.format == "vastu_revit_layout_v1"
    assert result.io_bundle.autocad.format == "vastu_autocad_layout_v1"
    assert len(result.io_bundle.revit.rooms) == len(payload.elements)
    assert "complete" in result.pipeline_stages


@pytest.mark.asyncio
async def test_revit_io_has_plot_and_rooms(generator):
    payload = _multi_room_payload()
    result = await generator.generate(
        GenerateLayoutFromReportRequest(payload=payload, use_llm_planner=False, generate_svg_preview=False)
    )

    revit = result.io_bundle.revit
    assert len(revit.plot_boundary) >= 3
    for room in revit.rooms:
        assert len(room.polygon) >= 3
        assert room.area > 0
        assert room.zone


@pytest.mark.asyncio
async def test_autocad_dxf_blueprint_entities(generator):
    payload = _multi_room_payload()
    result = await generator.generate(
        GenerateLayoutFromReportRequest(payload=payload, use_llm_planner=False, generate_svg_preview=False)
    )

    blueprint = result.io_bundle.autocad.dxf_blueprint
    assert "layers" in blueprint
    assert "entities" in blueprint
    assert any(entity["layer"] == "VASTU_PLOT" for entity in blueprint["entities"])
    assert any(entity["layer"] == "VASTU_ROOMS" for entity in blueprint["entities"])


@pytest.mark.asyncio
async def test_dxf_bytes_export(generator):
    payload = _multi_room_payload()
    result = await generator.generate(
        GenerateLayoutFromReportRequest(payload=payload, use_llm_planner=False, generate_svg_preview=False)
    )

    try:
        dxf_bytes = layout_to_dxf_bytes(result.layout)
    except RuntimeError:
        pytest.skip("ezdxf not installed")
    assert len(dxf_bytes) > 100
    assert dxf_bytes.startswith(b"  0")


@pytest.mark.asyncio
async def test_fixed_room_constraint_respected(generator):
    payload = _multi_room_payload()
    kitchen_polygon = list(payload.elements[0].polygon)
    result = await generator.generate(
        GenerateLayoutFromReportRequest(
            payload=payload,
            use_llm_planner=False,
            generate_svg_preview=False,
            user_constraints=[
                UserLayoutConstraint(
                    constraint_id="lock-kitchen",
                    kind=UserConstraintKind.fixed_room,
                    room_id="r-kitchen",
                )
            ],
        )
    )

    kitchen = next(room for room in result.layout.rooms if room.room_id == "r-kitchen")
    assert len(kitchen.polygon) == len(kitchen_polygon)
    assert "r-kitchen" in result.constraint_validation.skipped_corrections


@pytest.mark.asyncio
async def test_zone_placement_no_duplicate_room_ids():
    payload = _multi_room_payload()
    pipeline = get_pipeline()
    report = await pipeline.run(AnalyzeComplianceRequest(payload=payload))
    orientations = report.orientations
    targets = resolve_target_zones_from_report(orientations, report.rule_results)

    room_polygons = [element.polygon for element in payload.elements if element.element_type == ElementType.room]
    plot_center = shapely_ops.compute_plot_center(room_polygons)
    plot_radius = shapely_ops.compute_plot_radius(room_polygons, plot_center)
    plot_boundary = compute_plot_boundary(room_polygons)

    engine = ZonePlacementEngine()
    placements = engine.place_rooms(
        orientations=orientations,
        target_zones=targets,
        plot_center=plot_center,
        plot_radius=plot_radius,
        plot_boundary=plot_boundary,
        true_north_degrees=0,
        locked_polygons={},
        resolve_zone=pipeline.direction_engine.resolve_zone,
    )

    ids = [room.room_id for room in placements]
    assert len(ids) == len(set(ids))


def test_api_generate_from_report_endpoint():
    client = TestClient(app)
    payload = _multi_room_payload()
    response = client.post(
        "/api/v1/layout/generate-from-report",
        json={
            "payload": payload.model_dump(mode="json"),
            "use_llm_planner": False,
            "generate_svg_preview": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["layout"]["rooms"]
    assert body["io_bundle"]["revit"]["rooms"]


@pytest.mark.asyncio
async def test_mcp_generate_layout_from_report():
    server = MCPServer(get_pipeline())
    payload = _multi_room_payload()
    response = await server.call_tool(
        MCPToolCallRequest(
            tool="generate_layout_from_report",
            arguments={
                "payload": payload.model_dump(mode="json"),
                "use_llm_planner": False,
                "generate_svg_preview": False,
            },
        )
    )
    assert response.status == "ok"
    assert response.result["layout"]["rooms"]
