from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.schemas import ComplianceReport, LayoutImageBundle
from app.services.report.branding import report_branding_context
from app.services.report.formatter import ReportFormatter


class HtmlReportGenerator:
    """Production HTML report generator with branding, 2D and 3D comparison visuals."""

    def __init__(self, formatter: ReportFormatter | None = None) -> None:
        self._formatter = formatter or ReportFormatter()
        template_dir = Path(__file__).resolve().parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate(
        self,
        report: ComplianceReport,
        *,
        layout_images: LayoutImageBundle | None = None,
        isometric_original: str | None = None,
        isometric_corrected: str | None = None,
    ) -> str:
        structured = self._formatter.build(report)
        exec_sum = structured["executive_summary"]
        score = exec_sum["compliance_score"]
        score_pct = min(100, max(0, score))

        corrected_summary = structured.get("corrected_layout") or {}
        corrected_score = corrected_summary.get("corrected_compliance_score")
        score_improved = corrected_summary.get("compliance_improved")

        context = {
            **report_branding_context(),
            "request_id": exec_sum["request_id"],
            "generated_at": exec_sum["generated_at"],
            "headline": exec_sum["headline"],
            "score": score,
            "score_pct": score_pct,
            "grade": exec_sum["grade"],
            "total_rooms": exec_sum["total_rooms"],
            "passed_rules": exec_sum["passed_rules"],
            "failed_rules": exec_sum["failed_rules"],
            "auto_fixes": exec_sum["auto_fixes"],
            "manual_fixes": exec_sum["manual_fixes"],
            "remediation_summary": structured["remediation_summary"],
            "priority_fixes": structured["priority_fixes"],
            "room_dashboard": structured["room_dashboard"],
            "zone_legend": structured["zone_legend"],
            "corrected_score": corrected_score,
            "score_improved": score_improved,
            "layout_original": layout_images.original.content if layout_images and layout_images.original else None,
            "layout_corrected": layout_images.corrected.content if layout_images and layout_images.corrected else None,
            "layout_comparison": layout_images.comparison.content if layout_images and layout_images.comparison else None,
            "iso_original": isometric_original,
            "iso_corrected": isometric_corrected,
        }

        template = self._env.get_template("vastu_report.html")
        return template.render(**context)

    def save_path_hint(self, request_id: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = request_id.replace(":", "-")[:32]
        return f"VastuReport_{safe_id}_{stamp}.html"
