import pytest

from app.api.deps import get_pipeline
from app.models.schemas import (
    AnalyzeComplianceRequest,
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    Point2D,
)
from app.services.remediation.planner import RemediationPlanner


@pytest.mark.asyncio
async def test_pipeline_includes_remediation_plan():
    get_pipeline.cache_clear()
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
            ],
        )
    )
    pipeline = get_pipeline()
    report = await pipeline.run(request)

    assert report.remediation_plan is not None
    assert report.remediation_plan.summary
    assert isinstance(report.remediation_plan.actions, list)


def test_remediation_planner_builds_auto_and_manual_actions():
    from app.models.schemas import (
        AIRecommendation,
        Point2D,
        RoomOrientation,
        RuleEvaluationResult,
        Severity,
    )

    planner = RemediationPlanner()
    orientations = [
        RoomOrientation(
            room_id="r1",
            room_name="Kitchen",
            room_type="kitchen",
            area=50,
            centroid=Point2D(x=1, y=1),
            orientation_degrees=200,
            zone="south",
            confidence=0.9,
        )
    ]
    failures = [
        RuleEvaluationResult(
            rule_id="VR-001",
            title="Kitchen SE",
            passed=False,
            room_id="r1",
            zone="south",
            expected_zones=["south_east"],
            avoided_zones=["north_east"],
            severity=Severity.high,
            score_impact=10,
            confidence=0.9,
            explanation="Kitchen in wrong zone",
        )
    ]
    recs = [
        AIRecommendation(
            room_id="r1",
            recommendation="Move kitchen toward south-east",
            rationale="Kitchen in wrong zone",
            confidence=0.9,
            severity=Severity.high,
        )
    ]

    plan = planner.build_plan(failures, orientations, recs)
    assert plan.actions
    action_types = {action.action_type.value for action in plan.actions}
    assert "move_room_boundaries" in action_types
    assert "draw_zone_guide" in action_types
    assert "show_ghost_design" in action_types
    assert "move_centroid_toward_zone" not in action_types
    move = next(a for a in plan.actions if a.action_type.value == "move_room_boundaries")
    assert "translation_feet" in move.parameters
    assert move.parameters["translation_feet"]["x"] != 0 or move.parameters["translation_feet"]["y"] != 0
