"""Build a corrected 2D floor plan by applying Vastu suggestion geometry to the original layout."""

from __future__ import annotations

from app.models.schemas import (
    AppliedLayoutChange,
    CorrectedLayoutResult,
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    GhostOverlayPayload,
    GhostRoomCorrection,
)
from app.services.correction.constraint_validator import LayoutConstraintValidator
from app.services.correction.transforms import translate_polygon
from app.services.direction.engine import DirectionEngine
from app.services.geometry.engine import GeometryEngine
from app.services.rules.engine import VastuRuleEngine
from app.services.scoring.compliance import ComplianceScoringEngine


class CorrectedLayoutBuilder:
    """
    Produces the same 2D layout with suggested room moves applied.

    Preserves room topology (same IDs, names, types, wall links) while updating
    polygons to match ghost-overlay / remediation suggestions.
    """

    def __init__(
        self,
        geometry_engine: GeometryEngine | None = None,
        direction_engine: DirectionEngine | None = None,
        rule_engine: VastuRuleEngine | None = None,
        scoring_engine: ComplianceScoringEngine | None = None,
        validator: LayoutConstraintValidator | None = None,
    ) -> None:
        self._geometry = geometry_engine or GeometryEngine()
        self._direction = direction_engine or DirectionEngine()
        self._rule_engine = rule_engine
        self._scoring = scoring_engine or ComplianceScoringEngine()
        self._validator = validator or LayoutConstraintValidator(rule_engine)

    def build_from_ghost(
        self,
        original: FloorPlanPayload,
        ghost: GhostOverlayPayload,
        *,
        original_compliance_score: float,
    ) -> CorrectedLayoutResult:
        correction_map = {item.room_id: item for item in ghost.room_corrections}
        corrected_elements = self._apply_corrections(original.elements, correction_map)
        corrected_payload = FloorPlanPayload(
            source="vastu_corrected_2d",
            true_north_degrees=original.true_north_degrees,
            levels=list(original.levels),
            elements=corrected_elements,
            model_reference=original.model_reference,
        )

        corrected_orientations = self._geometry.build_room_orientations(
            corrected_payload,
            zone_resolver=self._direction.resolve_zone,
        )
        corrected_results = (
            self._rule_engine.evaluate(corrected_orientations)
            if self._rule_engine is not None
            else []
        )
        corrected_summary = self._scoring.compute_summary(
            len(corrected_orientations),
            corrected_results,
        )

        changes = [self._to_applied_change(item) for item in ghost.room_corrections]
        corrected_room_ids = set(correction_map.keys())
        all_room_ids = [
            element.id
            for element in original.elements
            if element.element_type == ElementType.room
        ]
        unchanged = [room_id for room_id in all_room_ids if room_id not in corrected_room_ids]

        validation = self._validator.validate_ghost_overlay(ghost, rule_engine=self._rule_engine)
        if self._rule_engine is not None:
            layout_validation = self._validator.validate_corrected_payload(
                corrected_payload,
                corrected_orientations,
                rule_engine=self._rule_engine,
            )
            validation = {**validation, **layout_validation}

        return CorrectedLayoutResult(
            original_source=original.source,
            corrected_payload=corrected_payload,
            changes_applied=changes,
            unchanged_room_ids=unchanged,
            original_compliance_score=original_compliance_score,
            corrected_compliance_score=corrected_summary.compliance_score,
            compliance_improved=corrected_summary.compliance_score >= original_compliance_score,
            validation=validation,
        )

    def build(
        self,
        original: FloorPlanPayload,
        ghost: GhostOverlayPayload,
        *,
        original_compliance_score: float,
    ) -> CorrectedLayoutResult:
        return self.build_from_ghost(
            original,
            ghost,
            original_compliance_score=original_compliance_score,
        )

    def _apply_corrections(
        self,
        elements: list[FloorPlanElement],
        correction_map: dict[str, GhostRoomCorrection],
    ) -> list[FloorPlanElement]:
        updated: list[FloorPlanElement] = []

        for element in elements:
            if element.element_type == ElementType.room and element.id in correction_map:
                correction = correction_map[element.id]
                updated.append(
                    element.model_copy(
                        update={
                            "polygon": list(correction.corrected_polygon),
                            "metadata": {
                                **element.metadata,
                                "vastu_corrected": True,
                                "original_zone": correction.original_zone,
                                "corrected_zone": correction.corrected_zone,
                                "target_zone": correction.target_zone,
                                "translation_applied": correction.translation,
                            },
                        }
                    )
                )
                continue

            linked_room_id = str(element.metadata.get("room_id", ""))
            correction = correction_map.get(linked_room_id)
            if correction is not None and element.polygon:
                translation = correction.translation
                updated.append(
                    element.model_copy(
                        update={
                            "polygon": translate_polygon(
                                element.polygon,
                                translation["x"],
                                translation["y"],
                            ),
                            "metadata": {
                                **element.metadata,
                                "vastu_corrected": True,
                                "linked_room_id": linked_room_id,
                            },
                        }
                    )
                )
                continue

            updated.append(element.model_copy(deep=True))

        return updated

    @staticmethod
    def _to_applied_change(correction: GhostRoomCorrection) -> AppliedLayoutChange:
        return AppliedLayoutChange(
            room_id=correction.room_id,
            room_name=correction.room_name,
            room_type=correction.room_type,
            original_zone=correction.original_zone,
            target_zone=correction.target_zone,
            corrected_zone=correction.corrected_zone,
            translation=correction.translation,
            rule_ids=list(correction.rule_ids),
            compliance_improved=correction.compliance_improved,
        )
