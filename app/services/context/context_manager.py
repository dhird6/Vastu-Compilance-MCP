from __future__ import annotations

from uuid import uuid4


class ComplianceContextManager:
    def build_context(self, request_context: dict) -> dict:
        return {
            "request_id": request_context.get("request_id", str(uuid4())),
            "client": request_context.get("client", "unknown"),
            "project_id": request_context.get("project_id", "unknown"),
            "correlation_tags": request_context.get("correlation_tags", []),
        }
