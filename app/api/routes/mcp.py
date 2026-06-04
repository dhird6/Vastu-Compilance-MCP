from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_pipeline
from app.mcp.server import MCPServer
from app.models.schemas import (
    MCPInitializeRequest,
    MCPInitializeResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
)
from app.services.compliance_pipeline import CompliancePipeline

router = APIRouter(prefix="/mcp", tags=["mcp"])


def get_mcp_server(pipeline: CompliancePipeline = Depends(get_pipeline)) -> MCPServer:
    return MCPServer(pipeline=pipeline)


@router.post("/initialize", response_model=MCPInitializeResponse)
async def initialize(
    request: MCPInitializeRequest,
    server: MCPServer = Depends(get_mcp_server),
) -> MCPInitializeResponse:
    return await server.initialize(request)


@router.get("/tools")
async def tools(server: MCPServer = Depends(get_mcp_server)) -> dict:
    return await server.list_tools()


@router.post("/tools/call", response_model=MCPToolCallResponse)
async def call_tool(
    request: MCPToolCallRequest,
    server: MCPServer = Depends(get_mcp_server),
) -> MCPToolCallResponse:
    return await server.call_tool(request)
