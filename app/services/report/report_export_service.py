"""Bundle compliance reports for download (HTML + JSON + visual assets)."""

from __future__ import annotations

import base64
import json
import zipfile
from dataclasses import dataclass
from io import BytesIO

from app.models.schemas import ComplianceReport, LayoutImageBundle
from app.services.report.html_generator import HtmlReportGenerator


@dataclass(frozen=True)
class ReportDownloadBundle:
    filename: str
    html: str
    json_payload: str
    zip_base64: str
    assets: dict[str, str]


class ReportExportService:
    def __init__(self, html_generator: HtmlReportGenerator | None = None) -> None:
        self._html = html_generator or HtmlReportGenerator()

    def build_download_bundle(
        self,
        report: ComplianceReport,
        *,
        layout_images: LayoutImageBundle | None = None,
        isometric_original: str | None = None,
        isometric_corrected: str | None = None,
        project_name: str | None = None,
    ) -> ReportDownloadBundle:
        html = report.html_report
        if not html:
            html = self._html.generate(
                report,
                layout_images=layout_images,
                isometric_original=isometric_original,
                isometric_corrected=isometric_corrected,
            )

        filename = self._html.save_path_hint(report.request_id)
        if project_name:
            safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in project_name)[:40]
            filename = f"VastuReport_{safe}_{report.request_id[:12]}.html"

        json_payload = json.dumps(report.model_dump(mode="json"), indent=2, default=str)
        zip_base64 = self._build_zip(
            filename=filename,
            html=html,
            json_payload=json_payload,
            layout_images=layout_images,
            isometric_original=isometric_original,
            isometric_corrected=isometric_corrected,
        )

        assets: dict[str, str] = {}
        if layout_images:
            if layout_images.original:
                assets["layout_original.svg"] = layout_images.original.content
            if layout_images.corrected:
                assets["layout_corrected.svg"] = layout_images.corrected.content
            if layout_images.comparison:
                assets["layout_comparison.svg"] = layout_images.comparison.content
        if isometric_original:
            assets["isometric_original.svg"] = isometric_original
        if isometric_corrected:
            assets["isometric_corrected.svg"] = isometric_corrected

        return ReportDownloadBundle(
            filename=filename,
            html=html,
            json_payload=json_payload,
            zip_base64=zip_base64,
            assets=assets,
        )

    @staticmethod
    def _build_zip(
        *,
        filename: str,
        html: str,
        json_payload: str,
        layout_images: LayoutImageBundle | None,
        isometric_original: str | None,
        isometric_corrected: str | None,
    ) -> str:
        buffer = BytesIO()
        base = filename.replace(".html", "")
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(filename, html)
            archive.writestr(f"{base}.json", json_payload)
            if layout_images:
                if layout_images.original:
                    archive.writestr("assets/layout_original.svg", layout_images.original.content)
                if layout_images.corrected:
                    archive.writestr("assets/layout_corrected.svg", layout_images.corrected.content)
                if layout_images.comparison:
                    archive.writestr("assets/layout_comparison.svg", layout_images.comparison.content)
            if isometric_original:
                archive.writestr("assets/isometric_original.svg", isometric_original)
            if isometric_corrected:
                archive.writestr("assets/isometric_corrected.svg", isometric_corrected)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
