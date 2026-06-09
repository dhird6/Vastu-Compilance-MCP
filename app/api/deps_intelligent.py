from __future__ import annotations

from functools import lru_cache

from app.api.deps import get_pipeline
from app.services.extraction.vlm_layout_extractor import VlmLayoutExtractor
from app.services.pipeline.intelligent_layout_pipeline import IntelligentLayoutPipeline


@lru_cache(maxsize=1)
def get_intelligent_pipeline() -> IntelligentLayoutPipeline:
    return IntelligentLayoutPipeline(
        compliance_pipeline=get_pipeline(),
        vlm_extractor=VlmLayoutExtractor(),
    )
