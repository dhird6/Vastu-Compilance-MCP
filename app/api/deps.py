from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.plugins.manager import PluginManager
from app.services.ai.explainer import ExplainableAIEngine
from app.services.compliance_pipeline import CompliancePipeline
from app.services.context.context_manager import ComplianceContextManager
from app.services.direction.engine import DirectionEngine
from app.services.geometry.engine import GeometryEngine
from app.services.knowledge.vedic_knowledge import VedicKnowledgeService
from app.services.remediation.planner import RemediationPlanner
from app.services.rules.engine import VastuRuleEngine
from app.services.scoring.compliance import ComplianceScoringEngine
from app.services.validation.geometry_validator import GeometryValidator
from app.services.visualization.overlay import VisualizationEngine


@lru_cache(maxsize=1)
def get_pipeline() -> CompliancePipeline:
    settings = get_settings()
    plugin_manager = PluginManager()
    knowledge_service = VedicKnowledgeService(settings.resolved_vedic_knowledge_path)
    plugin_manager.load(settings.enabled_plugin_paths)
    return CompliancePipeline(
        geometry_engine=GeometryEngine(),
        direction_engine=DirectionEngine(),
        rule_engine=VastuRuleEngine(settings.resolved_rules_path),
        ai_engine=ExplainableAIEngine(knowledge_service=knowledge_service),
        scoring_engine=ComplianceScoringEngine(),
        validator=GeometryValidator(),
        visualization_engine=VisualizationEngine(),
        context_manager=ComplianceContextManager(),
        plugin_manager=plugin_manager,
        remediation_planner=RemediationPlanner(DirectionEngine()),
    )
