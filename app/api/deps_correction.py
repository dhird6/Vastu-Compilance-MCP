from __future__ import annotations

from functools import lru_cache

from app.api.deps import get_pipeline
from app.core.config import get_settings
from app.services.correction.constraint_validator import LayoutConstraintValidator
from app.services.correction.corrected_layout import CorrectedLayoutBuilder
from app.services.correction.ghost_overlay import GhostOverlayEngine
from app.services.correction.layout_generator import LayoutGeneratorEngine
from app.services.direction.engine import DirectionEngine
from app.services.geometry.engine import GeometryEngine
from app.services.rules.engine import VastuRuleEngine
from app.services.scoring.compliance import ComplianceScoringEngine


@lru_cache(maxsize=1)
def get_ghost_engine() -> GhostOverlayEngine:
    settings = get_settings()
    rule_engine = VastuRuleEngine(settings.resolved_rules_path)
    return GhostOverlayEngine(
        geometry_engine=GeometryEngine(),
        direction_engine=DirectionEngine(),
        validator=LayoutConstraintValidator(rule_engine),
    )


@lru_cache(maxsize=1)
def get_layout_generator() -> LayoutGeneratorEngine:
    settings = get_settings()
    rule_engine = VastuRuleEngine(settings.resolved_rules_path)
    return LayoutGeneratorEngine(
        geometry_engine=GeometryEngine(),
        direction_engine=DirectionEngine(),
        rule_engine=rule_engine,
        validator=LayoutConstraintValidator(rule_engine),
    )


@lru_cache(maxsize=1)
def get_corrected_layout_builder() -> CorrectedLayoutBuilder:
    settings = get_settings()
    rule_engine = VastuRuleEngine(settings.resolved_rules_path)
    return CorrectedLayoutBuilder(
        geometry_engine=GeometryEngine(),
        direction_engine=DirectionEngine(),
        rule_engine=rule_engine,
        scoring_engine=ComplianceScoringEngine(),
        validator=LayoutConstraintValidator(rule_engine),
    )


async def analyze_payload_for_correction(request_payload):
    """Run compliance pipeline to obtain orientations + rule results."""
    from app.models.schemas import AnalyzeComplianceRequest

    pipeline = get_pipeline()
    report = await pipeline.run(AnalyzeComplianceRequest(payload=request_payload))
    return report.orientations, report.rule_results, report.summary.compliance_score
