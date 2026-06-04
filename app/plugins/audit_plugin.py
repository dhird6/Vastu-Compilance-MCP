from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.plugins.base import CompliancePlugin


class AuditStampPlugin(CompliancePlugin):
    name = "audit_stamp"

    async def before_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("plugin_trace", []).append(
            {"plugin": self.name, "stage": "before", "at": datetime.now(timezone.utc).isoformat()}
        )
        return payload

    async def after_evaluation(self, report: dict[str, Any]) -> dict[str, Any]:
        report.setdefault("context", {})
        report["context"].setdefault("plugin_trace", []).append(
            {"plugin": self.name, "stage": "after", "at": datetime.now(timezone.utc).isoformat()}
        )
        return report
