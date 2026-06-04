import pytest

from app.models.schemas import (
    AutocadEntity2D,
    AutocadEntityType,
    AutocadLayoutPayload,
    BoundingBox3D,
    Point2D,
    Point3D,
    RevitElement3D,
    RevitElementType,
    RevitModelPayload,
)
from app.services.geometry.engine import GeometryEngine


@pytest.mark.asyncio
async def test_project_revit_3d_to_floorplan_preserves_room_metadata():
    engine = GeometryEngine()
    payload = RevitModelPayload(
        elements=[
            RevitElement3D(
                id="rv-1",
                name="Kitchen",
                element_type=RevitElementType.room,
                bounding_box=BoundingBox3D(
                    min=Point3D(x=0, y=0, z=0),
                    max=Point3D(x=10, y=8, z=3),
                ),
                metadata={"room_type": "kitchen"},
            )
        ]
    )
    floorplan = await engine.project_revit_3d_to_floorplan(payload)
    assert floorplan.source == "revit_3d_projection"
    assert len(floorplan.elements) == 1
    room = floorplan.elements[0]
    assert room.metadata["room_type"] == "kitchen"
    assert room.metadata["projection_mode"] == "xy_footprint"
    assert room.metadata["source_3d_bbox_height"] == 3.0


@pytest.mark.asyncio
async def test_project_autocad_layout_to_floorplan_maps_entities():
    engine = GeometryEngine()
    payload = AutocadLayoutPayload(
        layout_name="GF",
        entities=[
            AutocadEntity2D(
                id="ac-1",
                name="Kitchen",
                entity_type=AutocadEntityType.room,
                points=[
                    Point2D(x=0, y=0),
                    Point2D(x=8, y=0),
                    Point2D(x=8, y=6),
                    Point2D(x=0, y=6),
                ],
                metadata={"room_type": "kitchen"},
            )
        ],
    )
    floorplan = await engine.project_autocad_layout_to_floorplan(payload)
    assert floorplan.source == "direct_json"
    assert len(floorplan.elements) == 1
    room = floorplan.elements[0]
    assert room.metadata["layout_name"] == "GF"
    assert room.metadata["source_entity_type"] == "room"
