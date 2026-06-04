from __future__ import annotations

from app.models.schemas import (
    AnalyzeAutocadComplianceRequest,
    AnalyzeComplianceRequest,
    AnalyzeRevitComplianceRequest,
    AnalyzeRevitDeltaComplianceRequest,
    ComplianceChatRequest,
    EvaluateRoomRequest,
    KnowledgeIngestRequest,
    MCPInitializeRequest,
    MCPInitializeResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
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
