"""Generate new 2D layout from Vastu compliance report + export Revit/AutoCAD I/O."""

from __future__ import annotations

import base64
from uuid import uuid4

from app.models.schemas import (
    AnalyzeComplianceRequest,
    AutocadLayoutExport,
    ComplianceReport,
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    GenerateLayoutFromReportRequest,
    GenerateLayoutFromReportResponse,
    GeneratedLayoutDocument,
    GeneratedLayoutMetadata,
    GeneratedRoomPlacement,
    LayoutExportFormat,
    LayoutImageBundle,
    LayoutIoBundle,
    LayoutIoFormat,
    RevitLayoutExport,
    RevitLayoutRoom,
    UserLayoutConstraint,
)
from app.services.ai.layout_planner import LayoutPlannerAI
from app.services.compliance_pipeline import CompliancePipeline
from app.services.constraints.user_constraints import UserConstraintEngine
from app.services.correction.constraint_validator import LayoutConstraintValidator
from app.services.correction.dxf_exporter import export_layout_to_dxf_dict, layout_to_dxf_bytes
from app.services.correction.transforms import compute_plot_boundary
from app.services.correction.zone_placement_engine import (
    ZonePlacementEngine,
    resolve_target_zones_from_report,
)
from app.services.direction.engine import DirectionEngine
from app.services.geometry import shapely_ops
from app.services.geometry.engine import GeometryEngine
from app.services.rules.engine import VastuRuleEngine
from app.services.scoring.compliance import ComplianceScoringEngine
from app.services.visualization.layout_image_renderer import LayoutImageRenderer


class ReportLayoutGenerator:
    """
    Report-driven new 2D layout generator.

    Input: original floor plan + compliance report (+ optional user constraints)
    Output: GeneratedLayoutDocument + Revit JSON + AutoCAD DXF blueprint
    """

    def __init__(
        self,
        compliance_pipeline: CompliancePipeline,
        *,
        geometry_engine: GeometryEngine | None = None,
        direction_engine: DirectionEngine | None = None,
        rule_engine: VastuRuleEngine | None = None,
        scoring_engine: ComplianceScoringEngine | None = None,
        constraint_engine: UserConstraintEngine | None = None,
        placement_engine: ZonePlacementEngine | None = None,
        layout_planner: LayoutPlannerAI | None = None,
        image_renderer: LayoutImageRenderer | None = None,
    ) -> None:
        self._compliance = compliance_pipeline
        self._geometry = geometry_engine or compliance_pipeline.geometry_engine
        self._direction = direction_engine or compliance_pipeline.direction_engine
        self._rule_engine = rule_engine or compliance_pipeline.rule_engine
        self._scoring = scoring_engine or compliance_pipeline.scoring_engine
        self._constraints = constraint_engine or UserConstraintEngine()
        self._placement = placement_engine or ZonePlacementEngine()
        self._planner = layout_planner or LayoutPlannerAI()
        self._images = image_renderer or LayoutImageRenderer()
        self._validator = LayoutConstraintValidator(self._rule_engine)

    async def generate(self, request: GenerateLayoutFromReportRequest) -> GenerateLayoutFromReportResponse:
        stages: list[str] = ["load_report"]

        report = request.report
        if report is None:
            stages.append("run_compliance")
            report = await self._compliance.run(
                AnalyzeComplianceRequest(payload=request.payload, context=request.context)
            )

        orientations = report.orientations or self._geometry.build_room_orientations(
            request.payload, zone_resolver=self._direction.resolve_zone
        )
        rule_results = report.rule_results or self._rule_engine.evaluate(orientations)
        locked = self._constraints.resolve_locked_room_ids(request.user_constraints, request.payload)

        stages.append("plan_zones")
        if request.use_llm_planner:
            llm_assignments = self._planner.plan(
                orientations=orientations,
                rule_results=rule_results,
                locked_room_ids=locked,
                constraints=request.user_constraints,
            )
            strategy = "hybrid" if self._planner.enabled else "deterministic"
        else:
            llm_assignments = []
            strategy = "deterministic"

        target_zones = resolve_target_zones_from_report(orientations, rule_results)
        for assignment in llm_assignments:
            target_zones[assignment.room_id] = assignment.target_zone
        for constraint in request.user_constraints:
            if constraint.kind.value == "fixed_zone" and constraint.room_id and constraint.zone:
                target_zones[constraint.room_id] = constraint.zone

        room_polygons = [
            element.polygon
            for element in request.payload.elements
            if element.element_type == ElementType.room
        ]
        plot_center = shapely_ops.compute_plot_center(room_polygons)
        plot_radius = shapely_ops.compute_plot_radius(room_polygons, plot_center)
        plot_boundary = compute_plot_boundary(room_polygons)

        locked_polygons = {
            element.id: list(element.polygon)
            for element in request.payload.elements
            if element.element_type == ElementType.room and element.id in locked
        }

        stages.append("place_rooms")
        placements = self._placement.place_rooms(
            orientations=orientations,
            target_zones=target_zones,
            plot_center=plot_center,
            plot_radius=plot_radius,
            plot_boundary=plot_boundary,
            true_north_degrees=request.payload.true_north_degrees,
            locked_polygons=locked_polygons,
            resolve_zone=self._direction.resolve_zone,
        )

        generated_orientations = _placements_to_orientations(placements)
        generated_results = self._rule_engine.evaluate(generated_orientations)
        original_summary = self._scoring.compute_summary(len(orientations), rule_results)
        generated_summary = self._scoring.compute_summary(len(placements), generated_results)

        layout = GeneratedLayoutDocument(
            metadata=GeneratedLayoutMetadata(
                true_north_degrees=request.payload.true_north_degrees,
                plot_center=plot_center,
                plot_boundary=plot_boundary,
                original_compliance_score=original_summary.compliance_score,
                generated_compliance_score=generated_summary.compliance_score,
                source_request_id=report.request_id or str(uuid4()),
                generation_strategy=strategy,
                llm_model=self._planner._model if self._planner.enabled else None,
            ),
            rooms=placements,
            walls=_synthetic_walls(placements),
        )
        layout.validation = self._validator.validate_generated_layout(layout, rule_engine=self._rule_engine)

        stages.append("build_io_bundle")
        io_bundle = self._build_io_bundle(
            layout,
            request.payload,
            export_formats=request.export_formats,
        )

        corrected_payload = io_bundle.floor_plan_payload
        corrected_result = _corrected_from_layout(layout, request.payload, original_summary.compliance_score)
        constraint_validation = self._constraints.validate_correction(
            original=request.payload,
            corrected=corrected_result,
            constraints=request.user_constraints,
            orientations=orientations,
        )
        constraint_validation.skipped_corrections = sorted(locked)

        layout_images = LayoutImageBundle()
        if request.generate_svg_preview:
            stages.append("render_svg")
            layout_images = self._images.render_bundle(
                request.payload,
                corrected_payload,
                locked_room_ids=locked,
            )

        stages.append("complete")
        return GenerateLayoutFromReportResponse(
            layout=layout,
            io_bundle=io_bundle,
            constraint_validation=constraint_validation,
            llm_assignments=llm_assignments,
            layout_images=layout_images,
            pipeline_stages=stages,
        )

    def _build_io_bundle(
        self,
        layout: GeneratedLayoutDocument,
        original: FloorPlanPayload,
        *,
        export_formats: list[LayoutIoFormat],
    ) -> LayoutIoBundle:
        floor_plan = _layout_to_floor_plan(layout)
        revit = RevitLayoutExport(
            true_north_degrees=layout.metadata.true_north_degrees,
            plot_boundary=layout.metadata.plot_boundary,
            plot_center=layout.metadata.plot_center,
            rooms=[
                RevitLayoutRoom(
                    id=room.room_id,
                    name=room.room_name,
                    room_type=room.room_type,
                    zone=room.zone,
                    polygon=room.polygon,
                    area=room.area,
                    metadata={"source": room.source, "vastu_generated": True},
                )
                for room in layout.rooms
            ],
            walls=layout.walls,
            compliance_score=layout.metadata.generated_compliance_score,
            original_compliance_score=layout.metadata.original_compliance_score,
            source_request_id=layout.metadata.source_request_id,
            generation_strategy=layout.metadata.generation_strategy,
        )

        dxf_blueprint = export_layout_to_dxf_dict(layout)
        dxf_base64 = None
        if LayoutIoFormat.dxf in export_formats:
            try:
                dxf_base64 = base64.b64encode(layout_to_dxf_bytes(layout)).decode("ascii")
            except RuntimeError:
                dxf_base64 = None

        autocad = AutocadLayoutExport(
            dxf_blueprint=dxf_blueprint,
            dxf_base64=dxf_base64,
            filename_hint=f"vastu_layout_{layout.metadata.source_request_id}.dxf",
            compliance_score=layout.metadata.generated_compliance_score,
            original_compliance_score=layout.metadata.original_compliance_score,
        )

        layout.export_artifacts = {
            "vastu_layout_json": layout.model_dump(mode="json"),
            "revit_io": revit.model_dump(mode="json"),
            "autocad_io": autocad.model_dump(mode="json"),
        }
        if dxf_blueprint:
            layout.export_artifacts["dxf"] = dxf_blueprint

        return LayoutIoBundle(
            floor_plan_payload=floor_plan,
            revit=revit,
            autocad=autocad,
            layout_document=layout,
        )


def _placements_to_orientations(placements: list[GeneratedRoomPlacement]) -> list:
    from app.models.schemas import RoomOrientation

    return [
        RoomOrientation(
            room_id=room.room_id,
            room_name=room.room_name,
            room_type=room.room_type,
            area=room.area,
            centroid=room.centroid,
            orientation_degrees=0.0,
            zone=room.zone,
            confidence=0.95,
        )
        for room in placements
    ]


def _synthetic_walls(placements: list[GeneratedRoomPlacement]) -> list[FloorPlanElement]:
    walls: list[FloorPlanElement] = []
    for room in placements:
        for index in range(len(room.polygon)):
            start = room.polygon[index]
            end = room.polygon[(index + 1) % len(room.polygon)]
            walls.append(
                FloorPlanElement(
                    id=f"wall-{room.room_id}-{index}",
                    name=f"Wall {room.room_name} {index}",
                    element_type=ElementType.wall,
                    polygon=[start, end],
                    metadata={"room_id": room.room_id, "synthetic": True, "vastu_generated": True},
                )
            )
    return walls


def _layout_to_floor_plan(layout: GeneratedLayoutDocument) -> FloorPlanPayload:
    elements: list[FloorPlanElement] = []
    for room in layout.rooms:
        elements.append(
            FloorPlanElement(
                id=room.room_id,
                name=room.room_name,
                element_type=ElementType.room,
                polygon=room.polygon,
                metadata={"room_type": room.room_type, "zone": room.zone, "vastu_generated": True},
            )
        )
    elements.extend(layout.walls)
    return FloorPlanPayload(
        source="vastu_corrected_2d",
        true_north_degrees=layout.metadata.true_north_degrees,
        elements=elements,
    )


def _corrected_from_layout(
    layout: GeneratedLayoutDocument,
    original: FloorPlanPayload,
    original_score: float,
):
    from app.models.schemas import CorrectedLayoutResult

    payload = _layout_to_floor_plan(layout)
    return CorrectedLayoutResult(
        original_source=original.source,
        corrected_payload=payload,
        original_compliance_score=original_score,
        corrected_compliance_score=layout.metadata.generated_compliance_score,
        compliance_improved=layout.metadata.generated_compliance_score >= original_score,
    )
