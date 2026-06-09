from __future__ import annotations

from app.models.schemas import (
    AnalyzeAutocadComplianceRequest,
    AnalyzeComplianceRequest,
    AnalyzeRevitComplianceRequest,
    AnalyzeRevitDeltaComplianceRequest,
    ApplySuggestionsRequest,
    ComplianceChatRequest,
    EvaluateRoomRequest,
    GenerateGhostOverlayRequest,
    IntelligentLayoutRequest,
    KnowledgeIngestRequest,
    MCPInitializeRequest,
    MCPInitializeResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
    ReportDownloadRequest,
    ResolveZoneRequest,
)
from app.services.chat.assistant import ComplianceChatAssistant
from app.services.compliance_pipeline import CompliancePipeline
from app.mcp.tools import ThinMCPTools

_TOOL_NAMES = [
    "analyze_floorplan",
    "analyze_vastu_compliance",
    "analyze_revit_3d_vastu_compliance",
    "analyze_autocad_layout_vastu_compliance",
    "vastu_score",
    "suggest_improvements",
    "detect_violations",
    "room_analysis",
    "compliance_chat",
    "ingest_vedic_knowledge",
    "list_rules",
    "directional_zones",
    "evaluate_room",
    "resolve_zone",
    "check_brahmasthan",
    "intelligent_layout_analyze",
    "extract_layout_geometry",
    "generate_ghost_overlay",
    "generate_layout_from_report",
    "download_vastu_report",
]


class MCPServer:
    def __init__(self, pipeline: CompliancePipeline) -> None:
        self.pipeline = pipeline
        self._chat = ComplianceChatAssistant()
        self._thin = ThinMCPTools(pipeline)

    async def initialize(self, request: MCPInitializeRequest) -> MCPInitializeResponse:
        return MCPInitializeResponse(
            protocol_version=request.protocol_version,
            server_name="vastu-compliance-mcp",
            server_version="3.0.0",
            capabilities={"tools": _TOOL_NAMES, "structuredOutput": True},
        )

    async def list_tools(self) -> dict:
        return {
            "tools": [
                {"name": "analyze_floorplan", "description": "Analyze 2D floor plan geometry for Vastu compliance."},
                {"name": "analyze_vastu_compliance", "description": "Alias for analyze_floorplan."},
                {"name": "analyze_revit_3d_vastu_compliance", "description": "Analyze Revit 3D model footprints."},
                {"name": "analyze_autocad_layout_vastu_compliance", "description": "Analyze AutoCAD 2D layout."},
                {"name": "vastu_score", "description": "Return compliance score and grade from a report or payload."},
                {"name": "suggest_improvements", "description": "Return remediation plan actions for failed rules."},
                {"name": "detect_violations", "description": "Return failed rule evaluations only."},
                {"name": "room_analysis", "description": "Return orientation and rules for one room_id."},
                {"name": "compliance_chat", "description": "Conversational assistant for compliance questions."},
                {"name": "ingest_vedic_knowledge", "description": "Ingest Vedic/Puran guidance entries."},
                {"name": "list_rules", "description": "Return loaded Vastu rules."},
                {"name": "directional_zones", "description": "Return 8-zone compass map with Sanskrit names."},
                {"name": "evaluate_room", "description": "Stateless single-room evaluate (element_id, polygon, room_type)."},
                {"name": "resolve_zone", "description": "Map bearing degrees to Vastu zone."},
                {"name": "check_brahmasthan", "description": "Detect Brahmasthan overlap for a room."},
                {
                    "name": "intelligent_layout_analyze",
                    "description": (
                        "Full pipeline: extract 2D layout (VLM or payload) → Vastu report → "
                        "constrained correction → layout SVG images. Supports user_constraints."
                    ),
                },
                {
                    "name": "extract_layout_geometry",
                    "description": "Extract rooms/walls/doors/windows from image_base64 or payload only.",
                },
                {
                    "name": "generate_ghost_overlay",
                    "description": "Non-destructive ghost overlay + corrected layout from floor plan.",
                },
                {
                    "name": "apply_layout_suggestions",
                    "description": "Apply Vastu suggestions to same 2D layout (respects user_constraints).",
                },
                {
                    "name": "generate_layout_from_report",
                    "description": (
                        "Generate NEW 2D Vastu-compliant layout from report. "
                        "Returns Revit JSON + AutoCAD DXF I/O bundle."
                    ),
                },
                {
                    "name": "download_vastu_report",
                    "description": (
                        "Build downloadable Vastu report with company logo, 2D layout comparison, "
                        "3D isometric views, priority fixes, and ZIP bundle (html + json + svg assets)."
                    ),
                },
            ]
        }

    async def call_tool(self, request: MCPToolCallRequest) -> MCPToolCallResponse:
        tool = request.tool
        args = request.arguments

        if tool in {"analyze_floorplan", "analyze_vastu_compliance"}:
            report = await self.pipeline.run(AnalyzeComplianceRequest.model_validate(args))
            return _ok(tool, {"report": report.model_dump(mode="json")})

        if tool == "analyze_revit_3d_vastu_compliance":
            report = await self.pipeline.run_for_revit_3d(
                AnalyzeRevitComplianceRequest.model_validate(args)
            )
            return _ok(tool, {"report": report.model_dump(mode="json")})

        if tool == "analyze_autocad_layout_vastu_compliance":
            report = await self.pipeline.run_for_autocad_layout(
                AnalyzeAutocadComplianceRequest.model_validate(args)
            )
            return _ok(tool, {"report": report.model_dump(mode="json")})

        if tool == "vastu_score":
            report = await self._report_from_args(args)
            return _ok(
                tool,
                {
                    "compliance_score": report.summary.compliance_score,
                    "grade": report.summary.grade,
                    "passed_rules": report.summary.passed_rules,
                    "failed_rules": report.summary.failed_rules,
                },
            )

        if tool == "suggest_improvements":
            report = await self._report_from_args(args)
            plan = report.remediation_plan
            return _ok(
                tool,
                {
                    "summary": plan.summary,
                    "actions": [action.model_dump(mode="json") for action in plan.actions],
                },
            )

        if tool == "detect_violations":
            report = await self._report_from_args(args)
            violations = [r.model_dump(mode="json") for r in report.rule_results if not r.passed]
            return _ok(tool, {"violations": violations, "count": len(violations)})

        if tool == "room_analysis":
            report = await self._report_from_args(args)
            room_id = str(args.get("room_id", ""))
            orientation = next((o for o in report.orientations if o.room_id == room_id), None)
            room_rules = [r.model_dump(mode="json") for r in report.rule_results if r.room_id == room_id]
            return _ok(
                tool,
                {
                    "room_id": room_id,
                    "orientation": orientation.model_dump(mode="json") if orientation else None,
                    "rule_results": room_rules,
                },
            )

        if tool == "compliance_chat":
            chat_req = ComplianceChatRequest.model_validate(args)
            response = self._chat.respond(chat_req, chat_req.report)
            return _ok(tool, response.model_dump(mode="json"))

        if tool == "ingest_vedic_knowledge":
            stats = self.pipeline.ai_engine.knowledge_service.ingest_entries(
                KnowledgeIngestRequest.model_validate(args).entries
            )
            return _ok(tool, stats)

        if tool == "list_rules":
            return _ok(tool, self.pipeline.rule_engine.registry.list_rules())

        if tool == "directional_zones":
            return _ok(tool, {"zones": self.pipeline.direction_engine.build_directional_zones()})

        if tool == "evaluate_room":
            return _ok(tool, self._thin.evaluate_room(EvaluateRoomRequest.model_validate(args)))

        if tool == "resolve_zone":
            return _ok(tool, self._thin.resolve_zone(ResolveZoneRequest.model_validate(args)))

        if tool == "check_brahmasthan":
            return _ok(tool, self._thin.check_brahmasthan(EvaluateRoomRequest.model_validate(args)))

        if tool == "intelligent_layout_analyze":
            from app.api.deps_intelligent import get_intelligent_pipeline

            response = await get_intelligent_pipeline().run(
                IntelligentLayoutRequest.model_validate(args)
            )
            return _ok(tool, response.model_dump(mode="json"))

        if tool == "extract_layout_geometry":
            from app.services.extraction.vlm_layout_extractor import VlmLayoutExtractor

            extraction = await VlmLayoutExtractor().extract(
                image_base64=args.get("image_base64"),
                image_media_type=args.get("image_media_type", "image/png"),
                payload=args.get("payload"),
                true_north_degrees=args.get("true_north_degrees"),
            )
            return _ok(tool, extraction.model_dump(mode="json"))

        if tool == "generate_ghost_overlay":
            from app.api.deps_correction import get_corrected_layout_builder, get_ghost_engine

            request = GenerateGhostOverlayRequest.model_validate(args)
            orientations = request.orientations
            rule_results = request.rule_results
            original_score = 100.0
            if orientations is None or rule_results is None:
                report = await self.pipeline.run(
                    AnalyzeComplianceRequest(payload=request.payload, context=request.context)
                )
                orientations = report.orientations
                rule_results = report.rule_results
                original_score = report.summary.compliance_score

            failed = [result for result in rule_results if not result.passed]
            ghost_engine = get_ghost_engine()
            layout_builder = get_corrected_layout_builder()
            ghost = ghost_engine.build(
                request.payload,
                rule_results=failed,
                orientations=orientations,
                shift_distance_feet=request.shift_distance_feet,
                source_request_id=request.context.get("request_id"),
            )
            corrected = (
                layout_builder.build_from_ghost(
                    request.payload, ghost, original_compliance_score=original_score
                )
                if ghost.room_corrections
                else None
            )
            return _ok(
                tool,
                {
                    "ghost_overlay": ghost.model_dump(mode="json"),
                    "corrected_layout": corrected.model_dump(mode="json") if corrected else None,
                },
            )

        if tool == "apply_layout_suggestions":
            from app.api.deps_correction import get_corrected_layout_builder, get_ghost_engine

            request = ApplySuggestionsRequest.model_validate(args)
            orientations = request.orientations
            rule_results = request.rule_results
            original_score = 100.0
            if orientations is None or rule_results is None:
                report = await self.pipeline.run(
                    AnalyzeComplianceRequest(payload=request.payload, context=request.context)
                )
                orientations = report.orientations
                rule_results = report.rule_results
                original_score = report.summary.compliance_score

            failed = [result for result in rule_results if not result.passed]
            if not failed:
                return _ok(
                    tool,
                    {
                        "corrected_layout": request.payload.model_dump(mode="json"),
                        "message": "No violations — layout unchanged.",
                    },
                )

            ghost_engine = get_ghost_engine()
            layout_builder = get_corrected_layout_builder()
            ghost = ghost_engine.build(
                request.payload,
                rule_results=failed,
                orientations=orientations,
                shift_distance_feet=request.shift_distance_feet,
                source_request_id=request.context.get("request_id"),
            )
            corrected = layout_builder.build_from_ghost(
                request.payload, ghost, original_compliance_score=original_score
            )
            payload = {"corrected_layout": corrected.model_dump(mode="json")}
            if request.include_ghost_overlay:
                payload["ghost_overlay"] = ghost.model_dump(mode="json")
            return _ok(tool, payload)

        if tool == "generate_layout_from_report":
            from app.api.deps_layout import get_report_layout_generator
            from app.models.schemas import GenerateLayoutFromReportRequest

            result = await get_report_layout_generator().generate(
                GenerateLayoutFromReportRequest.model_validate(args)
            )
            return _ok(tool, result.model_dump(mode="json"))

        if tool == "download_vastu_report":
            from app.services.report.report_export_service import ReportExportService

            request = ReportDownloadRequest.model_validate(args)
            bundle = ReportExportService().build_download_bundle(
                request.report,
                project_name=request.project_name,
            )
            return _ok(
                tool,
                {
                    "filename": bundle.filename,
                    "html": bundle.html,
                    "zip_base64": bundle.zip_base64,
                    "assets": bundle.assets,
                    "message": "Save HTML for browser view or decode zip_base64 for full package.",
                },
            )

        return MCPToolCallResponse(tool=tool, status="error", error=f"Unknown tool: {tool}")

    async def _report_from_args(self, args: dict):
        if "report" in args:
            from app.models.schemas import ComplianceReport

            return ComplianceReport.model_validate(args["report"])
        if "payload" in args and args.get("source") == "revit_3d":
            return await self.pipeline.run_for_revit_3d(
                AnalyzeRevitComplianceRequest.model_validate(args)
            )
        if "room_ids" in args:
            delta = AnalyzeRevitDeltaComplianceRequest.model_validate(args)
            return await self.pipeline.run_for_revit_3d_delta(
                payload=delta.payload,
                room_ids=delta.room_ids,
                request_context=delta.context,
            )
        return await self.pipeline.run(AnalyzeComplianceRequest.model_validate(args))


def _ok(tool: str, result: dict) -> MCPToolCallResponse:
    return MCPToolCallResponse(tool=tool, status="ok", result=result)
