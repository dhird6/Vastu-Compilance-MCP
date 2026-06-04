import pytest

from app.api.deps import get_pipeline
from app.models.schemas import (
    AnalyzeAutocadComplianceRequest,
    AnalyzeComplianceRequest,
    AnalyzeRevitComplianceRequest,
    AutocadEntity2D,
    AutocadEntityType,
    AutocadLayoutPayload,
    BoundingBox3D,
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    KnowledgeIngestRequest,
    Point2D,
    Point3D,
    RevitElement3D,
    RevitElementType,
    RevitModelPayload,
    VedicKnowledgeEntry,
)


@pytest.mark.asyncio
async def test_pipeline_generates_structured_report():
    request = AnalyzeComplianceRequest(
        payload=FloorPlanPayload(
            source="direct_json",
            true_north_degrees=0,
            elements=[
                FloorPlanElement(
                    id="r1",
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
                    id="r2",
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
            ],
        ),
        context={"client": "pytest"},
    )
    pipeline = get_pipeline()
    report = await pipeline.run(request)

    assert report.summary.total_rooms == 2
    assert isinstance(report.summary.compliance_score, float)
    assert report.request_id
    assert report.orientations
    assert report.heatmap


@pytest.mark.asyncio
async def test_revit_3d_projection_pipeline_generates_report():
    request = AnalyzeRevitComplianceRequest(
        payload=RevitModelPayload(
            true_north_degrees=0,
            elements=[
                RevitElement3D(
                    id="r3d-1",
                    name="Kitchen",
                    element_type=RevitElementType.room,
                    bounding_box=BoundingBox3D(
                        min=Point3D(x=0, y=0, z=0),
                        max=Point3D(x=10, y=8, z=3),
                    ),
                    metadata={"room_type": "kitchen"},
                )
            ],
        ),
        context={"client": "pytest-revit"},
    )
    pipeline = get_pipeline()
    report = await pipeline.run_for_revit_3d(request)
    assert report.summary.total_rooms == 1
    assert report.orientations[0].room_type == "kitchen"


@pytest.mark.asyncio
async def test_autocad_layout_pipeline_generates_report():
    request = AnalyzeAutocadComplianceRequest(
        payload=AutocadLayoutPayload(
            true_north_degrees=0,
            layout_name="Ground Floor",
            entities=[
                AutocadEntity2D(
                    id="acad-room-1",
                    name="Kitchen",
                    entity_type=AutocadEntityType.room,
                    points=[
                        Point2D(x=0, y=0),
                        Point2D(x=9, y=0),
                        Point2D(x=9, y=7),
                        Point2D(x=0, y=7),
                    ],
                    metadata={"room_type": "kitchen"},
                )
            ],
        ),
        context={"client": "pytest-autocad"},
    )
    pipeline = get_pipeline()
    report = await pipeline.run_for_autocad_layout(request)
    assert report.summary.total_rooms == 1
    assert report.orientations[0].room_type == "kitchen"


@pytest.mark.asyncio
async def test_ingested_vedic_knowledge_is_used_in_recommendations():
    pipeline = get_pipeline()
    ingest = KnowledgeIngestRequest(
        entries=[
            VedicKnowledgeEntry(
                source="Test Purana",
                principle="Kitchen directional guidance",
                room_types=["kitchen"],
                preferred_zones=["south_east"],
                avoid_zones=["north"],
                guidance="Kitchen should avoid north in this test entry.",
            )
        ]
    )
    pipeline.ai_engine.knowledge_service.ingest_entries(ingest.entries)
    request = AnalyzeComplianceRequest(
        payload=FloorPlanPayload(
            source="direct_json",
            true_north_degrees=0,
            elements=[
                FloorPlanElement(
                    id="rk-1",
                    name="Kitchen",
                    element_type=ElementType.room,
                    polygon=[
                        Point2D(x=0, y=0),
                        Point2D(x=10, y=0),
                        Point2D(x=10, y=8),
                        Point2D(x=0, y=8),
                    ],
                    metadata={"room_type": "kitchen"},
                )
            ],
        ),
        context={"client": "pytest-knowledge"},
    )
    report = await pipeline.run(request)
    assert report.recommendations
    assert report.recommendations[0].scriptural_references
