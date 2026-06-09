from __future__ import annotations



from fastapi import APIRouter, Depends



from app.api.deps_correction import (

    analyze_payload_for_correction,

    get_corrected_layout_builder,

    get_ghost_engine,

    get_layout_generator,

)

from app.models.schemas import (

    ApplySuggestionsRequest,

    ApplySuggestionsResponse,

    CorrectedLayoutResult,

    GenerateGhostOverlayRequest,

    GenerateGhostOverlayResponse,

    GenerateLayoutRequest,

    GenerateLayoutResponse,

)

from app.services.correction.corrected_layout import CorrectedLayoutBuilder

from app.services.correction.ghost_overlay import GhostOverlayEngine

from app.services.correction.layout_generator import LayoutGeneratorEngine



router = APIRouter(prefix="/api/v1/correction", tags=["correction"])





def _unchanged_layout_result(payload, original_score: float) -> CorrectedLayoutResult:

    return CorrectedLayoutResult(

        original_source=payload.source,

        corrected_payload=payload,

        original_compliance_score=original_score,

        corrected_compliance_score=original_score,

        compliance_improved=False,

        validation={"message": "No violations — layout unchanged."},

    )





@router.post("/ghost-overlay", response_model=GenerateGhostOverlayResponse)

async def generate_ghost_overlay(

    request: GenerateGhostOverlayRequest,

    engine: GhostOverlayEngine = Depends(get_ghost_engine),

    layout_builder: CorrectedLayoutBuilder = Depends(get_corrected_layout_builder),

) -> GenerateGhostOverlayResponse:

    orientations = request.orientations

    rule_results = request.rule_results

    original_score = 100.0

    if orientations is None or rule_results is None:

        orientations, rule_results, original_score = await analyze_payload_for_correction(

            request.payload

        )



    failed = [result for result in rule_results if not result.passed]

    ghost = engine.build(

        request.payload,

        rule_results=failed,

        orientations=orientations,

        shift_distance_feet=request.shift_distance_feet,

        source_request_id=request.context.get("request_id"),

    )

    corrected_layout = (

        layout_builder.build_from_ghost(request.payload, ghost, original_compliance_score=original_score)

        if ghost.room_corrections

        else _unchanged_layout_result(request.payload, original_score)

    )

    return GenerateGhostOverlayResponse(

        ghost_overlay=ghost,

        corrected_layout=corrected_layout,

        remediation_compatible=True,

    )





@router.post("/apply-suggestions", response_model=ApplySuggestionsResponse)

async def apply_suggestions_to_layout(

    request: ApplySuggestionsRequest,

    engine: GhostOverlayEngine = Depends(get_ghost_engine),

    layout_builder: CorrectedLayoutBuilder = Depends(get_corrected_layout_builder),

) -> ApplySuggestionsResponse:

    """Return the same 2D layout with all Vastu suggestion moves applied."""

    orientations = request.orientations

    rule_results = request.rule_results

    original_score = 100.0

    if orientations is None or rule_results is None:

        orientations, rule_results, original_score = await analyze_payload_for_correction(

            request.payload

        )



    failed = [result for result in rule_results if not result.passed]

    if not failed:

        return ApplySuggestionsResponse(

            corrected_layout=_unchanged_layout_result(request.payload, original_score),

            ghost_overlay=None,

        )



    ghost = engine.build(

        request.payload,

        rule_results=failed,

        orientations=orientations,

        shift_distance_feet=request.shift_distance_feet,

        source_request_id=request.context.get("request_id"),

    )

    corrected_layout = layout_builder.build_from_ghost(

        request.payload,

        ghost,

        original_compliance_score=original_score,

    )

    return ApplySuggestionsResponse(

        corrected_layout=corrected_layout,

        ghost_overlay=ghost if request.include_ghost_overlay else None,

    )





@router.post("/generate-layout", response_model=GenerateLayoutResponse)

async def generate_layout(

    request: GenerateLayoutRequest,

    engine: LayoutGeneratorEngine = Depends(get_layout_generator),

) -> GenerateLayoutResponse:

    orientations = request.orientations

    rule_results = request.rule_results

    if orientations is None or rule_results is None:

        orientations, rule_results, _ = await analyze_payload_for_correction(request.payload)



    layout, prompt_context = engine.generate(

        request.payload,

        orientations=orientations,

        rule_results=rule_results,

        llm_assignments=request.llm_assignments,

        export_format=request.export_format,

        target_compliance_score=request.target_compliance_score,

        source_request_id=request.context.get("request_id"),

    )

    return GenerateLayoutResponse(layout=layout, llm_prompt_context=prompt_context)


