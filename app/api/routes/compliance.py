from __future__ import annotations

import base64

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_pipeline
from app.models.schemas import (
    AnalyzeAutocadComplianceRequest,
    AnalyzeComplianceRequest,
    AnalyzeComplianceResponse,
    AnalyzeRevitComplianceRequest,
    AnalyzeRevitDeltaComplianceRequest,
    ComplianceChatRequest,
    ComplianceChatResponse,
    ComplianceReport,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    ReportDownloadRequest,
    ReportDownloadResponse,
    RulesListResponse,
)
from app.services.report.html_generator import HtmlReportGenerator
from app.services.report.report_export_service import ReportExportService
from app.services.chat.assistant import ComplianceChatAssistant
from app.services.compliance_pipeline import CompliancePipeline

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])
_chat = ComplianceChatAssistant()
_report_export = ReportExportService()


@router.get("/rules", response_model=RulesListResponse)
async def list_rules(pipeline: CompliancePipeline = Depends(get_pipeline)) -> RulesListResponse:
    rules_data = pipeline.rule_engine.rules
    return RulesListResponse(
        rules=rules_data.get("rules", []),
        version=str(rules_data.get("version", "1")),
    )


@router.post("/analyze", response_model=AnalyzeComplianceResponse)
async def analyze_compliance(
    request: AnalyzeComplianceRequest,
    pipeline: CompliancePipeline = Depends(get_pipeline),
) -> AnalyzeComplianceResponse:
    report = await pipeline.run(request)
    return AnalyzeComplianceResponse(report=report)


@router.post("/analyze/revit3d", response_model=AnalyzeComplianceResponse)
async def analyze_revit_3d_compliance(
    request: AnalyzeRevitComplianceRequest,
    pipeline: CompliancePipeline = Depends(get_pipeline),
) -> AnalyzeComplianceResponse:
    report = await pipeline.run_for_revit_3d(request)
    return AnalyzeComplianceResponse(report=report)


@router.post("/analyze/revit3d/delta", response_model=AnalyzeComplianceResponse)
async def analyze_revit_3d_delta(
    request: AnalyzeRevitDeltaComplianceRequest,
    pipeline: CompliancePipeline = Depends(get_pipeline),
) -> AnalyzeComplianceResponse:
    report = await pipeline.run_for_revit_3d_delta(
        payload=request.payload,
        room_ids=request.room_ids,
        request_context=request.context,
    )
    return AnalyzeComplianceResponse(report=report)


@router.post("/analyze/autocad", response_model=AnalyzeComplianceResponse)
async def analyze_autocad_layout_compliance(
    request: AnalyzeAutocadComplianceRequest,
    pipeline: CompliancePipeline = Depends(get_pipeline),
) -> AnalyzeComplianceResponse:
    report = await pipeline.run_for_autocad_layout(request)
    return AnalyzeComplianceResponse(report=report)


@router.post("/knowledge/ingest", response_model=KnowledgeIngestResponse)
async def ingest_vedic_knowledge(
    request: KnowledgeIngestRequest,
    pipeline: CompliancePipeline = Depends(get_pipeline),
) -> KnowledgeIngestResponse:
    stats = pipeline.ai_engine.knowledge_service.ingest_entries(request.entries)
    return KnowledgeIngestResponse(**stats)


@router.post("/chat", response_model=ComplianceChatResponse)
async def compliance_chat(request: ComplianceChatRequest) -> ComplianceChatResponse:
    return _chat.respond(request, request.report)


@router.post("/report/html")
async def export_html_report(report: ComplianceReport) -> dict[str, str]:
    """Return professional HTML report for a compliance result."""
    generator = HtmlReportGenerator()
    return {
        "html": generator.generate(report),
        "filename": generator.save_path_hint(report.request_id),
    }


@router.post("/report/download", response_model=ReportDownloadResponse)
async def download_vastu_report(request: ReportDownloadRequest) -> ReportDownloadResponse:
    """Build downloadable report package: HTML with logo, 2D/3D comparison, JSON, ZIP."""
    bundle = _report_export.build_download_bundle(
        request.report,
        project_name=request.project_name,
    )
    return ReportDownloadResponse(
        filename=bundle.filename,
        html=bundle.html,
        zip_base64=bundle.zip_base64,
        assets=bundle.assets,
    )


@router.post("/report/download/zip")
async def download_vastu_report_zip(request: ReportDownloadRequest) -> Response:
    """Return report bundle as a ZIP file attachment."""
    bundle = _report_export.build_download_bundle(
        request.report,
        project_name=request.project_name,
    )
    zip_bytes = base64.b64decode(bundle.zip_base64)
    zip_name = bundle.filename.replace(".html", ".zip")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )
