import pytest

from app.api.deps import get_pipeline
from app.models.schemas import AnalyzeComplianceRequest, ElementType, FloorPlanElement, FloorPlanPayload, Point2D
from app.services.report.formatter import ReportFormatter
from app.services.report.html_generator import HtmlReportGenerator


@pytest.mark.asyncio
async def test_report_includes_structured_output_and_html():
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
                        Point2D(x=8, y=-8),
                        Point2D(x=12, y=-8),
                        Point2D(x=12, y=-4),
                        Point2D(x=8, y=-4),
                    ],
                    metadata={"room_type": "kitchen"},
                ),
            ],
        )
    )
    report = await get_pipeline().run(request)

    assert report.structured_output
    assert "executive_summary" in report.structured_output
    assert "room_dashboard" in report.structured_output
    assert "priority_fixes" in report.structured_output
    assert report.html_report
    assert "<!DOCTYPE html>" in report.html_report
    assert "Vastu Compliance Report" in report.html_report


def test_formatter_priority_fixes_sorted():
    from app.models.schemas import (
        AIRecommendation,
        ComplianceReport,
        ComplianceSummary,
        RemediationPlan,
        RoomOrientation,
        RuleEvaluationResult,
        Severity,
    )

    orientations = [
        RoomOrientation(
            room_id="r1",
            room_name="Kitchen",
            room_type="kitchen",
            area=50,
            centroid=Point2D(x=1, y=1),
            orientation_degrees=180,
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
            severity=Severity.high,
            score_impact=10,
            confidence=0.9,
            explanation="wrong zone",
        )
    ]
    report = ComplianceReport(
        request_id="test",
        summary=ComplianceSummary(
            total_rooms=1,
            passed_rules=0,
            failed_rules=1,
            compliance_score=55,
            grade="C",
        ),
        validation_issues=[],
        orientations=orientations,
        rule_results=failures,
        recommendations=[
            AIRecommendation(
                room_id="r1",
                recommendation="Move to SE",
                rationale="Fire zone",
                confidence=0.9,
                severity=Severity.high,
            )
        ],
        remediation_plan=RemediationPlan(),
        heatmap=[],
        overlays={},
    )
    structured = ReportFormatter().build(report)
    assert structured["priority_fixes"][0]["target_sanskrit"] == "Agneya"
    html = HtmlReportGenerator().generate(report)
    assert "Agneya" in html or "south_east" in html
