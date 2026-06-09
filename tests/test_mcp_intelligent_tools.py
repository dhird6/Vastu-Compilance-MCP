"""MCP tool tests for intelligent layout tools."""

from __future__ import annotations

import pytest

from app.api.deps import get_pipeline
from app.mcp.server import MCPServer
from app.models.schemas import MCPToolCallRequest


@pytest.fixture
def mcp_server() -> MCPServer:
    get_pipeline.cache_clear()
    return MCPServer(get_pipeline())


@pytest.mark.asyncio
async def test_mcp_lists_intelligent_tools(mcp_server: MCPServer):
    catalog = await mcp_server.list_tools()
    names = {item["name"] for item in catalog["tools"]}
    assert "intelligent_layout_analyze" in names
    assert "apply_layout_suggestions" in names


@pytest.mark.asyncio
async def test_mcp_intelligent_layout_analyze(mcp_server: MCPServer):
    response = await mcp_server.call_tool(
        MCPToolCallRequest(
            tool="intelligent_layout_analyze",
            arguments={
                "payload": {
                    "source": "direct_json",
                    "true_north_degrees": 0,
                    "elements": [
                        {
                            "id": "r-kitchen",
                            "name": "Kitchen",
                            "element_type": "room",
                            "polygon": [
                                {"x": 0, "y": 0},
                                {"x": 10, "y": 0},
                                {"x": 10, "y": 8},
                                {"x": 0, "y": 8},
                            ],
                            "metadata": {"room_type": "kitchen"},
                        }
                    ],
                },
                "generate_layout_images": True,
            },
        )
    )
    assert response.status == "ok"
    assert "extraction" in response.result
    assert "report" in response.result
    assert "layout_images" in response.result
