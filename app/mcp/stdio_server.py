"""Official MCP SDK stdio transport for Cursor / Claude Desktop."""

from __future__ import annotations

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from app.api.deps import get_pipeline
from app.mcp.server import MCPServer
from app.mcp.tools import ThinMCPTools
from app.models.schemas import (
    AnalyzeAutocadComplianceRequest,
    AnalyzeComplianceRequest,
    AnalyzeRevitComplianceRequest,
    ComplianceChatRequest,
    EvaluateRoomRequest,
    MCPToolCallRequest,
    ResolveZoneRequest,
)

mcp_app = Server("vastu-compliance-mcp")
_http_bridge: MCPServer | None = None
_thin: ThinMCPTools | None = None


def _bridge() -> MCPServer:
    global _http_bridge, _thin
    if _http_bridge is None:
        pipeline = get_pipeline()
        _http_bridge = MCPServer(pipeline)
        _thin = ThinMCPTools(pipeline)
    return _http_bridge


def _thin_tools() -> ThinMCPTools:
    _bridge()
    assert _thin is not None
    return _thin


@mcp_app.list_tools()
async def list_tools() -> list[Tool]:
    bridge = _bridge()
    catalog = await bridge.list_tools()
    extra = [
        Tool(
            name="evaluate_room",
            description="Stateless: evaluate one room by element_id, polygon, room_type, true_north.",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_id": {"type": "string"},
                    "room_name": {"type": "string"},
                    "room_type": {"type": "string"},
                    "polygon": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                            "required": ["x", "y"],
                        },
                    },
                    "true_north_degrees": {"type": "number", "default": 0},
                },
                "required": ["element_id", "room_name", "room_type", "polygon"],
            },
        ),
        Tool(
            name="resolve_zone",
            description="Map compass bearing (True North) to Vastu zone key and Sanskrit name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bearing_degrees": {"type": "number"},
                    "true_north_degrees": {"type": "number", "default": 0},
                },
                "required": ["bearing_degrees"],
            },
        ),
        Tool(
            name="check_brahmasthan",
            description="Check if room centroid overlaps Brahmasthan (center zone).",
            inputSchema=EvaluateRoomRequest.model_json_schema(),
        ),
    ]
    return [
        Tool(
            name=item["name"],
            description=item["description"],
            inputSchema={"type": "object", "additionalProperties": True},
        )
        for item in catalog["tools"]
    ] + extra


@mcp_app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    bridge = _bridge()
    thin = _thin_tools()

    if name == "evaluate_room":
        result = thin.evaluate_room(EvaluateRoomRequest.model_validate(arguments))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "resolve_zone":
        result = thin.resolve_zone(ResolveZoneRequest.model_validate(arguments))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "check_brahmasthan":
        result = thin.check_brahmasthan(EvaluateRoomRequest.model_validate(arguments))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    response = await bridge.call_tool(MCPToolCallRequest(tool=name, arguments=arguments))
    payload = {"status": response.status, "result": response.result, "error": response.error}
    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await mcp_app.run(read_stream, write_stream, mcp_app.create_initialization_options())


def run_stdio() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run_stdio()
