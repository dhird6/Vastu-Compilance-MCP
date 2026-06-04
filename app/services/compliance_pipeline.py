from __future__ import annotations

from app.models.schemas import (
    AnalyzeAutocadComplianceRequest,
    AnalyzeComplianceRequest,
    AnalyzeRevitComplianceRequest,
    ComplianceReport,
    RevitElementType,
    RevitModelPayload,
)
from app.plugins.manager import PluginManager
from app.services.ai.explainer import ExplainableAIEngine
from app.services.context.context_manager import ComplianceContextManager
from app.services.direction.engine import DirectionEngine
from app.services.geometry.engine import GeometryEngine
from app.services.remediation.planner import RemediationPlanner
from app.services.rules.engine import VastuRuleEngine
from app.services.scoring.compliance import ComplianceScoringEngine
from app.services.validation.geometry_validator import GeometryValidator
from app.services.report.formatter import ReportFormatter
from app.services.report.html_generator import HtmlReportGenerator
from app.services.visualization.overlay import VisualizationEngine


class CompliancePipeline:
    def __init__(
        self,
        geometry_engine: GeometryEngine,
        direction_engine: DirectionEngine,
        rule_engine: VastuRuleEngine,
        ai_engine: ExplainableAIEngine,
        scoring_engine: ComplianceScoringEngine,
        validator: GeometryValidator,
        visualization_engine: VisualizationEngine,
        context_manager: ComplianceContextManager,
        plugin_manager: PluginManager,
        remediation_planner: RemediationPlanner | None = None,
        report_formatter: ReportFormatter | None = None,
        html_generator: HtmlReportGenerator | None = None,
    ) -> None:
        self.geometry_engine = geometry_engine
        self.direction_engine = direction_engine
        self.rule_engine = rule_engine
        self.ai_engine = ai_engine
        self.scoring_engine = scoring_engine
        self.validator = validator
        self.visualization_engine = visualization_engine
        self.context_manager = context_manager
        self.plugin_manager = plugin_manager
        self.remediation_planner = remediation_planner or RemediationPlanner(direction_engine)
        self.report_formatter = report_formatter or ReportFormatter()
        self.html_generator = html_generator or HtmlReportGenerator(self.report_formatter)

    async def run(self, request: AnalyzeComplianceRequest) -> ComplianceReport:
        payload = await self.geometry_engine.extract_structured_elements(request.payload)
        return await self._run_for_payload(payload=payload, request_context=request.context)

    async def run_for_revit_3d(self, request: AnalyzeRevitComplianceRequest) -> ComplianceReport:
        payload = await self.geometry_engine.project_revit_3d_to_floorplan(request.payload)
        return await self._run_for_payload(payload=payload, request_context=request.context)

    async def run_for_autocad_layout(self, request: AnalyzeAutocadComplianceRequest) -> ComplianceReport:
        payload = await self.geometry_engine.project_autocad_layout_to_floorplan(request.payload)
        return await self._run_for_payload(payload=payload, request_context=request.context)

    async def run_for_revit_3d_delta(
        self,
        payload: RevitModelPayload,
        room_ids: list[str],
        request_context: dict,
    ) -> ComplianceReport:
        filtered = payload.model_copy(deep=True)
        if room_ids:
            allowed = set(room_ids)
            filtered.elements = [
                element
                for element in filtered.elements
                if element.element_type != RevitElementType.room or element.id in allowed
            ]
        projected = await self.geometry_engine.project_revit_3d_to_floorplan(filtered)
        context = {**request_context, "delta_mode": True, "room_ids": room_ids}
        return await self._run_for_payload(payload=projected, request_context=context)

    async def _run_for_payload(self, payload, request_context: dict) -> ComplianceReport:
        validation_issues = self.validator.validate(payload)

        payload_dict = payload.model_dump()
        payload_dict = await self.plugin_manager.run_before(payload_dict)

        orientations = self.geometry_engine.build_room_orientations(
            payload=payload,
            zone_resolver=self.direction_engine.resolve_zone,
        )
        results = self.rule_engine.evaluate(orientations)
        recommendations = self.ai_engine.generate_recommendations(results, orientations)
        failed_results = [result for result in results if not result.passed]
        remediation_plan = self.remediation_planner.build_plan(
            failed_results, orientations, recommendations
        )
        summary = self.scoring_engine.compute_summary(len(orientations), results)
        directional_zones = self.direction_engine.build_directional_zones()
        heatmap = self.visualization_engine.build_heatmap(orientations, results)
        overlays = self.visualization_engine.build_overlay_payload(orientations, directional_zones)
        context = self.context_manager.build_context(request_context)

        report = ComplianceReport(
            request_id=context["request_id"],
            summary=summary,
            validation_issues=validation_issues,
            orientations=orientations,
            rule_results=results,
            recommendations=recommendations,
            remediation_plan=remediation_plan,
            heatmap=heatmap,
            overlays=overlays,
            context=context,
            structured_output={},
            html_report=None,
        )
        report.structured_output = self.report_formatter.build(report)
        report.html_report = self.html_generator.generate(report)
        report_dict = await self.plugin_manager.run_after(report.model_dump(mode="json"))
        return ComplianceReport.model_validate(report_dict)
