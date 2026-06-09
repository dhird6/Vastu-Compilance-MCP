"""Tests for intelligent 2D layout pipeline (extract → Vastu → constrained image)."""

from __future__ import annotations

import pytest

from app.api.deps import get_pipeline
from app.api.deps_intelligent import get_intelligent_pipeline
from app.models.schemas import (
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    IntelligentLayoutRequest,
    Point2D,
    UserConstraintKind,
    UserLayoutConstraint,
)
from app.services.constraints.user_constraints import UserConstraintEngine
from app.services.extraction.vlm_layout_extractor import VlmLayoutExtractor
from app.services.visualization.layout_image_renderer import LayoutImageRenderer, svg_to_base64


def _sample_payload() -> FloorPlanPayload:
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
                name="Master",
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
    )


def pytest_runtest_setup():
    get_pipeline.cache_clear()
    get_intelligent_pipeline.cache_clear()


@pytest.mark.asyncio
async def test_vlm_extractor_from_payload():
    extractor = VlmLayoutExtractor()
    result = await extractor.extract(payload=_sample_payload())
    assert result.extraction_method == "direct_payload"
    assert len(result.elements) == 2
    assert result.confidence_score >= 0.9


@pytest.mark.asyncio
async def test_intelligent_pipeline_full_run():
    request = IntelligentLayoutRequest(payload=_sample_payload())
    response = await get_intelligent_pipeline().run(request)

    assert "extract_layout" in response.pipeline_stages
    assert "vastu_compliance" in response.pipeline_stages
    assert response.report.summary.total_rooms == 2
    assert response.layout_images.original is not None
    assert "<svg" in response.layout_images.original.content


@pytest.mark.asyncio
async def test_intelligent_pipeline_generates_corrected_layout_image():
    response = await get_intelligent_pipeline().run(
        IntelligentLayoutRequest(payload=_sample_payload())
    )
    if response.corrected_layout is not None:
        assert response.layout_images.corrected is not None
        assert response.layout_images.comparison is not None


def test_user_constraint_locks_fixed_room():
    engine = UserConstraintEngine()
    locked = engine.resolve_locked_room_ids(
        [
            UserLayoutConstraint(
                constraint_id="c1",
                kind=UserConstraintKind.fixed_room,
                room_id="r-master",
            )
        ],
        _sample_payload(),
    )
    assert locked == {"r-master"}


def test_user_constraint_filters_correctable_failures():
    from app.models.schemas import RuleEvaluationResult, Severity

    engine = UserConstraintEngine()
    failures = [
        RuleEvaluationResult(
            rule_id="VR-001",
            title="Kitchen SE",
            passed=False,
            room_id="r-kitchen",
            zone="south",
            expected_zones=["south_east"],
            severity=Severity.high,
            score_impact=10,
            confidence=0.9,
            explanation="wrong zone",
        ),
        RuleEvaluationResult(
            rule_id="VR-002",
            title="Master SW",
            passed=False,
            room_id="r-master",
            zone="east",
            expected_zones=["south_west"],
            severity=Severity.high,
            score_impact=9,
            confidence=0.9,
            explanation="wrong zone",
        ),
    ]
    allowed, skipped = engine.filter_correctable_failures(failures, {"r-master"})
    assert len(allowed) == 1
    assert allowed[0].room_id == "r-kitchen"
    assert "r-master" in skipped


@pytest.mark.asyncio
async def test_fixed_room_not_moved_in_intelligent_pipeline():
    response = await get_intelligent_pipeline().run(
        IntelligentLayoutRequest(
            payload=_sample_payload(),
            user_constraints=[
                UserLayoutConstraint(
                    constraint_id="keep-master",
                    kind=UserConstraintKind.fixed_room,
                    room_id="r-master",
                    reason="User preference",
                )
            ],
        )
    )
    assert "r-master" in response.constraint_validation.locked_room_ids
    if response.corrected_layout is not None:
        original_master = next(
            element for element in _sample_payload().elements if element.id == "r-master"
        )
        corrected_master = next(
            element
            for element in response.corrected_layout.corrected_payload.elements
            if element.id == "r-master"
        )
        assert original_master.polygon == corrected_master.polygon


def test_layout_image_renderer_produces_svg():
    renderer = LayoutImageRenderer()
    bundle = renderer.render_bundle(_sample_payload(), _sample_payload())
    assert bundle.original.content.startswith("<svg")
    assert "Original Layout" in bundle.original.content
    assert svg_to_base64(bundle.original)


def test_layout_image_marks_locked_rooms():
    renderer = LayoutImageRenderer()
    bundle = renderer.render_bundle(
        _sample_payload(),
        _sample_payload(),
        locked_room_ids={"r-master"},
    )
    assert "🔒" in bundle.corrected.content or "fixed" in bundle.comparison.content


@pytest.mark.asyncio
async def test_intelligent_api_endpoint():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/intelligent/analyze",
            json=IntelligentLayoutRequest(payload=_sample_payload()).model_dump(mode="json"),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["extraction_method"] == "direct_payload"
    assert "layout_images" in body


@pytest.mark.asyncio
async def test_vlm_extractor_requires_input():
    extractor = VlmLayoutExtractor()
    with pytest.raises(ValueError, match="Provide either"):
        await extractor.extract()
