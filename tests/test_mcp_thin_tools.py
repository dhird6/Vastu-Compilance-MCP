import pytest

from app.api.deps import get_pipeline
from app.models.schemas import EvaluateRoomRequest, Point2D, ResolveZoneRequest


@pytest.mark.asyncio
async def test_evaluate_room_mcp_tool():
    pipeline = get_pipeline()
    from app.mcp.tools import ThinMCPTools

    tools = ThinMCPTools(pipeline)
    result = tools.evaluate_room(
        EvaluateRoomRequest(
            element_id="r-kitchen",
            room_name="Kitchen",
            room_type="kitchen",
            true_north_degrees=0,
            polygon=[
                Point2D(x=8, y=-8),
                Point2D(x=12, y=-8),
                Point2D(x=12, y=-4),
                Point2D(x=8, y=-4),
            ],
            all_room_polygons={
                "r-bed": [
                    Point2D(x=-10, y=-10),
                    Point2D(x=-2, y=-10),
                    Point2D(x=-2, y=-2),
                    Point2D(x=-10, y=-2),
                ]
            },
        )
    )
    assert result["orientation"]["room_type"] == "kitchen"
    assert "rule_results" in result
    assert isinstance(result["passed"], bool)


def test_resolve_zone_tool():
    pipeline = get_pipeline()
    from app.mcp.tools import ThinMCPTools

    tools = ThinMCPTools(pipeline)
    result = tools.resolve_zone(ResolveZoneRequest(bearing_degrees=45, true_north_degrees=0))
    assert result["zone"] == "north_east"
    assert result["sanskrit"] == "Ishan"


def test_check_brahmasthan_center_room():
    pipeline = get_pipeline()
    from app.mcp.tools import ThinMCPTools

    tools = ThinMCPTools(pipeline)
    result = tools.check_brahmasthan(
        EvaluateRoomRequest(
            element_id="r-stair",
            room_name="Stair",
            room_type="staircase",
            polygon=[
                Point2D(x=-0.5, y=-0.5),
                Point2D(x=0.5, y=-0.5),
                Point2D(x=0.5, y=0.5),
                Point2D(x=-0.5, y=0.5),
            ],
            all_room_polygons={
                "r-outer": [
                    Point2D(x=-20, y=-20),
                    Point2D(x=20, y=-20),
                    Point2D(x=20, y=20),
                    Point2D(x=-20, y=20),
                ]
            },
        )
    )
    assert result["in_brahmasthan"] is True
    assert result["violation"] is True
