from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps_layout import get_report_layout_generator
from app.models.schemas import GenerateLayoutFromReportRequest, GenerateLayoutFromReportResponse
from app.services.correction.dxf_exporter import layout_to_dxf_bytes
from app.services.correction.report_layout_generator import ReportLayoutGenerator

router = APIRouter(prefix="/api/v1/layout", tags=["layout"])


@router.post("/generate-from-report", response_model=GenerateLayoutFromReportResponse)
async def generate_layout_from_report(
    request: GenerateLayoutFromReportRequest,
    generator: ReportLayoutGenerator = Depends(get_report_layout_generator),
) -> GenerateLayoutFromReportResponse:
    """
    Generate a **new** 2D Vastu-compliant layout from compliance report.

    Returns Revit JSON + AutoCAD DXF blueprint for plugin import.
    """
    return await generator.generate(request)


@router.post("/generate-from-report/dxf")
async def download_layout_dxf(
    request: GenerateLayoutFromReportRequest,
    generator: ReportLayoutGenerator = Depends(get_report_layout_generator),
) -> Response:
    """Download generated layout as DXF for AutoCAD."""
    result = await generator.generate(request)
    try:
        dxf_bytes = layout_to_dxf_bytes(result.layout)
    except RuntimeError as exc:
        return Response(content=str(exc), status_code=501, media_type="text/plain")

    filename = result.io_bundle.autocad.filename_hint or "vastu_layout.dxf"
    return Response(
        content=dxf_bytes,
        media_type="application/dxf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
