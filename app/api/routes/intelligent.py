from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps_intelligent import get_intelligent_pipeline
from app.models.schemas import IntelligentLayoutRequest, IntelligentLayoutResponse
from app.services.pipeline.intelligent_layout_pipeline import IntelligentLayoutPipeline

router = APIRouter(prefix="/api/v1/intelligent", tags=["intelligent"])


@router.post("/analyze", response_model=IntelligentLayoutResponse)
async def intelligent_layout_analyze(
    request: IntelligentLayoutRequest,
    pipeline: IntelligentLayoutPipeline = Depends(get_intelligent_pipeline),
) -> IntelligentLayoutResponse:
    """
    Full intelligent workflow:

    - Input: 2D layout image (VLM) OR structured FloorPlanPayload (CAD)
    - Extract rooms/walls/doors/windows
    - Run Vastu compliance + report with suggestions
    - Generate constrained corrected layout (respects user fixed rooms/zones)
    - Render original vs corrected layout SVG images
    """
    return await pipeline.run(request)
