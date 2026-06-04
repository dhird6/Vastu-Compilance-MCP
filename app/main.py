from __future__ import annotations

import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.api.routes.autodesk import router as autodesk_router
from app.api.routes.compliance import router as compliance_router
from app.api.routes.mcp import router as mcp_router
from app.core.config import get_settings
from app.core.logging import configure_logging, request_id_ctx_var

REQUEST_COUNTER = Counter("vastu_requests_total", "Total API requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("vastu_request_latency_seconds", "Request latency", ["method", "path"])

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Enterprise-grade Vastu Compliance MCP server for Autodesk integration.",
    debug=settings.app_debug,
)
app.include_router(compliance_router)
app.include_router(mcp_router)
app.include_router(autodesk_router)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request_id_ctx_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # pylint: disable=broad-except
        REQUEST_COUNTER.labels(request.method, request.url.path, "500").inc()
        raise exc
    elapsed = time.perf_counter() - start
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    REQUEST_COUNTER.labels(request.method, request.url.path, str(response.status_code)).inc()
    response.headers["x-request-id"] = request_id
    return response


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})
