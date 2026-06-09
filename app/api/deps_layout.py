from __future__ import annotations

from functools import lru_cache

from app.api.deps import get_pipeline
from app.services.ai.layout_planner import LayoutPlannerAI
from app.services.correction.report_layout_generator import ReportLayoutGenerator


@lru_cache(maxsize=1)
def get_report_layout_generator() -> ReportLayoutGenerator:
    return ReportLayoutGenerator(compliance_pipeline=get_pipeline(), layout_planner=LayoutPlannerAI())
