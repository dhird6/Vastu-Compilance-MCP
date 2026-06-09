"""Orchestrates: extract → Vastu → report → constrained correction → layout images."""

from __future__ import annotations

from app.models.schemas import (
    AnalyzeComplianceRequest,
    ConstraintValidationResult,
    CorrectedLayoutResult,
    IntelligentLayoutRequest,
    IntelligentLayoutResponse,
    LayoutImageBundle,
    LayoutExtractionResult,
    UserLayoutConstraint,
)
from app.services.compliance_pipeline import CompliancePipeline
from app.services.constraints.user_constraints import UserConstraintEngine
from app.services.correction.corrected_layout import CorrectedLayoutBuilder
from app.services.correction.ghost_overlay import GhostOverlayEngine
from app.services.extraction.vlm_layout_extractor import VlmLayoutExtractor
from app.services.visualization.layout_image_renderer import LayoutImageRenderer


class IntelligentLayoutPipeline:
    """
    End-to-end intelligent layout workflow:

    1. VLM/CAD extraction from 2D input
    2. Deterministic Vastu compliance + report
    3. Constrained correction (respect user fixed rooms/zones)
    4. SVG layout images (original vs Vastu-perfect)
    """

    def __init__(
        self,
        compliance_pipeline: CompliancePipeline,
        vlm_extractor: VlmLayoutExtractor | None = None,
        constraint_engine: UserConstraintEngine | None = None,
        ghost_engine: GhostOverlayEngine | None = None,
        corrected_builder: CorrectedLayoutBuilder | None = None,
        image_renderer: LayoutImageRenderer | None = None,
    ) -> None:
        self._compliance = compliance_pipeline
        self._vlm = vlm_extractor or VlmLayoutExtractor()
        self._constraints = constraint_engine or UserConstraintEngine()
        self._ghost = ghost_engine or GhostOverlayEngine()
        self._corrected = corrected_builder or CorrectedLayoutBuilder(
            geometry_engine=compliance_pipeline.geometry_engine,
            direction_engine=compliance_pipeline.direction_engine,
            rule_engine=compliance_pipeline.rule_engine,
            scoring_engine=compliance_pipeline.scoring_engine,
        )
        self._images = image_renderer or LayoutImageRenderer()

    async def run(self, request: IntelligentLayoutRequest) -> IntelligentLayoutResponse:
        stages: list[str] = []

        stages.append("extract_layout")
        extraction = await self._vlm.extract(
            image_base64=request.image_base64,
            image_media_type=request.image_media_type,
            payload=request.payload,
            true_north_degrees=request.true_north_degrees,
        )

        stages.append("vastu_compliance")
        report = await self._compliance.run(
            AnalyzeComplianceRequest(payload=extraction.payload, context=request.context)
        )

        locked = self._constraints.resolve_locked_room_ids(
            request.user_constraints,
            extraction.payload,
        )
        failed = [result for result in report.rule_results if not result.passed]
        correctable, skipped_ids = self._constraints.filter_correctable_failures(failed, locked)

        corrected_layout: CorrectedLayoutResult | None = None
        constraint_validation: ConstraintValidationResult

        if correctable:
            stages.append("constrained_correction")
            ghost = self._ghost.build(
                extraction.payload,
                rule_results=correctable,
                orientations=report.orientations,
                shift_distance_feet=request.shift_distance_feet,
                source_request_id=report.request_id,
            )
            ghost.room_corrections = [
                correction
                for correction in ghost.room_corrections
                if correction.room_id not in locked
            ]
            corrected_layout = self._corrected.build_from_ghost(
                extraction.payload,
                ghost,
                original_compliance_score=report.summary.compliance_score,
            )
            constraint_validation = self._constraints.validate_correction(
                original=extraction.payload,
                corrected=corrected_layout,
                constraints=request.user_constraints,
                orientations=report.orientations,
            )
            constraint_validation.skipped_corrections = sorted(set(skipped_ids))
        else:
            stages.append("no_correction_needed")
            constraint_validation = ConstraintValidationResult(
                valid=True,
                locked_room_ids=sorted(locked),
                skipped_corrections=sorted(set(skipped_ids)),
                violations=[],
                satisfied_constraints=[
                    constraint.constraint_id for constraint in request.user_constraints
                ],
            )
            if report.corrected_layout is not None:
                corrected_layout = report.corrected_layout

        layout_images: LayoutImageBundle = LayoutImageBundle()
        if request.generate_layout_images:
            stages.append("render_layout_images")
            corrected_payload = (
                corrected_layout.corrected_payload if corrected_layout is not None else None
            )
            layout_images = self._images.render_bundle(
                extraction.payload,
                corrected_payload,
                locked_room_ids=locked,
            )

        stages.append("complete")
        return IntelligentLayoutResponse(
            extraction=extraction,
            report=report,
            corrected_layout=corrected_layout,
            constraint_validation=constraint_validation,
            layout_images=layout_images,
            pipeline_stages=stages,
        )
