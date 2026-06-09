from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Point2D(BaseModel):
    x: float
    y: float


class Point3D(BaseModel):
    x: float
    y: float
    z: float


class BoundingBox3D(BaseModel):
    min: Point3D
    max: Point3D


class ElementType(str, Enum):
    room = "room"
    wall = "wall"
    door = "door"
    window = "window"


class FloorPlanElement(BaseModel):
    id: str
    name: str
    element_type: ElementType
    polygon: list[Point2D] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_polygon_points(self) -> "FloorPlanElement":
        if self.element_type == ElementType.room and len(self.polygon) < 3:
            raise ValueError("Room polygons must contain at least 3 points.")
        return self


class AutodeskModelReference(BaseModel):
    project_id: str
    urn: str
    version_id: str | None = None


class FloorPlanPayload(BaseModel):
    source: Literal[
        "aps",
        "direct_json",
        "revit_3d_projection",
        "vastu_corrected_2d",
        "vlm_extraction",
    ] = "direct_json"
    true_north_degrees: float = 0.0
    levels: list[str] = Field(default_factory=list)
    elements: list[FloorPlanElement] = Field(default_factory=list)
    model_reference: AutodeskModelReference | None = None


class GeometryValidationIssue(BaseModel):
    code: str
    message: str
    severity: Severity
    element_id: str | None = None


class RoomOrientation(BaseModel):
    room_id: str
    room_name: str
    room_type: str
    area: float
    centroid: Point2D
    orientation_degrees: float
    zone: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluateRoomRequest(BaseModel):
    """Stateless MCP input: single room geometry + parameters."""

    element_id: str
    room_name: str
    room_type: str
    polygon: list[Point2D]
    true_north_degrees: float = 0.0
    bounding_box: BoundingBox3D | None = None
    all_room_polygons: dict[str, list[Point2D]] = Field(default_factory=dict)


class ResolveZoneRequest(BaseModel):
    bearing_degrees: float
    true_north_degrees: float = 0.0


class ResolveZoneResponse(BaseModel):
    zone: str
    sanskrit: str
    element: str
    bearing_degrees: float


class AIExplanationRequest(BaseModel):
    rule_results: list[RuleEvaluationResult]
    orientations: list[RoomOrientation]


class RuleEvaluationResult(BaseModel):
    rule_id: str
    title: str
    passed: bool
    room_id: str
    zone: str
    expected_zones: list[str] = Field(default_factory=list)
    avoided_zones: list[str] = Field(default_factory=list)
    severity: Severity
    score_impact: float
    confidence: float
    explanation: str


class AIRecommendation(BaseModel):
    room_id: str
    recommendation: str
    rationale: str
    confidence: float
    severity: Severity
    scriptural_references: list[str] = Field(default_factory=list)


class HeatmapCell(BaseModel):
    room_id: str
    zone: str
    score: float
    color_hex: str
    status: Literal["compliant", "warning", "critical"]


class ComplianceSummary(BaseModel):
    total_rooms: int
    passed_rules: int
    failed_rules: int
    compliance_score: float
    grade: str


class RemediationActionType(str, Enum):
    set_parameter = "set_parameter"
    highlight_room = "highlight_room"
    rename_room_function = "rename_room_function"
    swap_room_function = "swap_room_function"
    move_centroid_toward_zone = "move_centroid_toward_zone"
    move_room_boundaries = "move_room_boundaries"
    draw_zone_guide = "draw_zone_guide"
    annotate = "annotate"
    show_ghost_design = "show_ghost_design"


class RemediationAction(BaseModel):
    action_id: str
    room_id: str
    rule_id: str
    action_type: RemediationActionType
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_user_approval: bool = False
    auto_applicable: bool = True
    confidence: float = 0.85


class RemediationPlan(BaseModel):
    actions: list[RemediationAction] = Field(default_factory=list)
    summary: str = ""
    auto_applicable_count: int = 0
    manual_approval_count: int = 0


class AppliedLayoutChange(BaseModel):
    """One room-level change applied to produce the corrected 2D layout."""

    room_id: str
    room_name: str
    room_type: str
    original_zone: str
    target_zone: str
    corrected_zone: str
    translation: dict[str, float]
    rule_ids: list[str] = Field(default_factory=list)
    compliance_improved: bool = False


class CorrectedLayoutResult(BaseModel):
    """
    Same 2D floor plan as input with Vastu suggestion geometry applied.

    Safe to render, export, or import as a new file — does not modify the source model.
    """

    version: str = "1.0"
    approach: Literal["same_layout_with_suggestions"] = "same_layout_with_suggestions"
    original_source: str
    corrected_payload: FloorPlanPayload
    changes_applied: list[AppliedLayoutChange] = Field(default_factory=list)
    unchanged_room_ids: list[str] = Field(default_factory=list)
    original_compliance_score: float
    corrected_compliance_score: float
    compliance_improved: bool = False
    validation: dict[str, Any] = Field(default_factory=dict)


class ComplianceReport(BaseModel):
    request_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: ComplianceSummary
    validation_issues: list[GeometryValidationIssue]
    orientations: list[RoomOrientation]
    rule_results: list[RuleEvaluationResult]
    recommendations: list[AIRecommendation]
    remediation_plan: RemediationPlan = Field(default_factory=lambda: RemediationPlan())
    corrected_layout: CorrectedLayoutResult | None = None
    heatmap: list[HeatmapCell]
    overlays: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    structured_output: dict[str, Any] = Field(default_factory=dict)
    html_report: str | None = None


class RevitElementType(str, Enum):
    room = "room"
    wall = "wall"
    door = "door"
    window = "window"


class RevitElement3D(BaseModel):
    id: str
    name: str
    element_type: RevitElementType
    bounding_box: BoundingBox3D
    metadata: dict[str, Any] = Field(default_factory=dict)


class RevitModelPayload(BaseModel):
    source: Literal["revit_3d"] = "revit_3d"
    true_north_degrees: float = 0.0
    levels: list[str] = Field(default_factory=list)
    elements: list[RevitElement3D] = Field(default_factory=list)
    model_reference: AutodeskModelReference | None = None


class AutocadEntityType(str, Enum):
    room = "room"
    wall = "wall"
    door = "door"
    window = "window"


class AutocadEntity2D(BaseModel):
    id: str
    name: str
    entity_type: AutocadEntityType
    points: list[Point2D] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutocadLayoutPayload(BaseModel):
    source: Literal["autocad_layout_2d"] = "autocad_layout_2d"
    true_north_degrees: float = 0.0
    layout_name: str = "Model"
    levels: list[str] = Field(default_factory=list)
    entities: list[AutocadEntity2D] = Field(default_factory=list)
    model_reference: AutodeskModelReference | None = None


class VedicKnowledgeEntry(BaseModel):
    source: str
    principle: str
    room_types: list[str] = Field(default_factory=list)
    preferred_zones: list[str] = Field(default_factory=list)
    avoid_zones: list[str] = Field(default_factory=list)
    guidance: str


class KnowledgeIngestRequest(BaseModel):
    entries: list[VedicKnowledgeEntry]


class KnowledgeIngestResponse(BaseModel):
    loaded_entries: int
    total_entries: int


class MCPInitializeRequest(BaseModel):
    protocol_version: str = "1.0"
    client_name: str = "autodesk-plugin"
    capabilities: dict[str, Any] = Field(default_factory=dict)


class MCPInitializeResponse(BaseModel):
    protocol_version: str = "1.0"
    server_name: str
    server_version: str
    capabilities: dict[str, Any]


class MCPToolCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    tool: str
    status: Literal["ok", "error"]
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AnalyzeComplianceRequest(BaseModel):
    payload: FloorPlanPayload
    context: dict[str, Any] = Field(default_factory=dict)


class AnalyzeComplianceResponse(BaseModel):
    report: ComplianceReport


class AnalyzeRevitComplianceRequest(BaseModel):
    payload: RevitModelPayload
    context: dict[str, Any] = Field(default_factory=dict)


class AnalyzeAutocadComplianceRequest(BaseModel):
    payload: AutocadLayoutPayload
    context: dict[str, Any] = Field(default_factory=dict)


class AnalyzeRevitDeltaComplianceRequest(BaseModel):
    payload: RevitModelPayload
    room_ids: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class ComplianceChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    report: ComplianceReport | None = None


class ComplianceChatResponse(BaseModel):
    reply: str
    cited_rule_ids: list[str] = Field(default_factory=list)


class RulesListResponse(BaseModel):
    rules: list[dict[str, Any]]
    version: str


# ---------------------------------------------------------------------------
# Layout auto-correction: Ghost Overlay (Approach 1) + Layout Generator (Approach 2)
# ---------------------------------------------------------------------------


class GhostElementKind(str, Enum):
    room_polygon = "room_polygon"
    wall_segment = "wall_segment"
    shift_arrow = "shift_arrow"
    zone_compass = "zone_compass"
    zone_wedge = "zone_wedge"
    label = "label"


class GhostRenderStyle(str, Enum):
    cyan_dashed = "cyan_dashed"
    gold_solid = "gold_solid"
    blue_thin = "blue_thin"
    red_warning = "red_warning"


class GhostGeometryElement(BaseModel):
    """Single drawable primitive for non-destructive overlay rendering."""

    element_id: str
    kind: GhostElementKind
    room_id: str | None = None
    rule_id: str | None = None
    geometry: dict[str, Any]
    style: GhostRenderStyle = GhostRenderStyle.cyan_dashed
    z_index: int = 10
    metadata: dict[str, Any] = Field(default_factory=dict)


class GhostRoomCorrection(BaseModel):
    """Per-room delta between original and proposed geometry."""

    room_id: str
    room_name: str
    room_type: str
    original_polygon: list[Point2D]
    corrected_polygon: list[Point2D]
    original_centroid: Point2D
    corrected_centroid: Point2D
    original_zone: str
    target_zone: str
    corrected_zone: str
    translation: dict[str, float]
    rule_ids: list[str] = Field(default_factory=list)
    compliance_improved: bool = False


class GhostOverlayMetadata(BaseModel):
    approach: Literal["ghost_overlay"] = "ghost_overlay"
    coordinate_system: Literal["plan_xy_y_north"] = "plan_xy_y_north"
    units: Literal["feet", "meters"] = "feet"
    true_north_degrees: float = 0.0
    plot_center: Point2D
    plot_boundary: list[Point2D]
    source_request_id: str | None = None
    plugin_render_hints: dict[str, Any] = Field(
        default_factory=lambda: {
            "revit_layer": "VASTU_GHOST_PREVIEW",
            "autocad_layer": "VASTU_GHOST",
            "opacity": 0.65,
            "non_destructive": True,
        }
    )


class GhostOverlayPayload(BaseModel):
    """
    Complete ghost overlay package sent to CAD plugin / web viewer.

    The plugin draws `elements` without modifying source model geometry.
    """

    version: str = "1.0"
    metadata: GhostOverlayMetadata
    room_corrections: list[GhostRoomCorrection] = Field(default_factory=list)
    elements: list[GhostGeometryElement] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)


class GenerateGhostOverlayRequest(BaseModel):
    payload: FloorPlanPayload
    rule_results: list[RuleEvaluationResult] | None = None
    orientations: list[RoomOrientation] | None = None
    shift_distance_feet: float = 3.0
    context: dict[str, Any] = Field(default_factory=dict)


class GenerateGhostOverlayResponse(BaseModel):
    ghost_overlay: GhostOverlayPayload
    corrected_layout: CorrectedLayoutResult | None = None
    remediation_compatible: bool = True


class ApplySuggestionsRequest(BaseModel):
    payload: FloorPlanPayload
    rule_results: list[RuleEvaluationResult] | None = None
    orientations: list[RoomOrientation] | None = None
    shift_distance_feet: float = 3.0
    include_ghost_overlay: bool = True
    context: dict[str, Any] = Field(default_factory=dict)


class ApplySuggestionsResponse(BaseModel):
    corrected_layout: CorrectedLayoutResult
    ghost_overlay: GhostOverlayPayload | None = None


class LayoutExportFormat(str, Enum):
    vastu_layout_json = "vastu_layout_json"
    dxf = "dxf"


class GeneratedRoomPlacement(BaseModel):
    room_id: str
    room_name: str
    room_type: str
    polygon: list[Point2D]
    area: float
    centroid: Point2D
    zone: str
    source: Literal["deterministic", "llm", "hybrid"] = "deterministic"


class GeneratedLayoutMetadata(BaseModel):
    approach: Literal["ai_layout_generator"] = "ai_layout_generator"
    coordinate_system: Literal["plan_xy_y_north"] = "plan_xy_y_north"
    units: Literal["feet", "meters"] = "feet"
    true_north_degrees: float = 0.0
    plot_center: Point2D
    plot_boundary: list[Point2D]
    original_compliance_score: float
    generated_compliance_score: float
    source_request_id: str | None = None
    llm_model: str | None = None
    generation_strategy: Literal["deterministic", "llm", "hybrid"] = "deterministic"


class GeneratedLayoutDocument(BaseModel):
    """New-instance layout (Approach 2) — safe to save as DXF/JSON without touching source."""

    version: str = "1.0"
    metadata: GeneratedLayoutMetadata
    rooms: list[GeneratedRoomPlacement] = Field(default_factory=list)
    walls: list[FloorPlanElement] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    export_artifacts: dict[str, Any] = Field(default_factory=dict)


class LLMRoomAssignment(BaseModel):
    """Structured LLM output stitched back into geometry."""

    room_id: str
    target_zone: str
    relative_position: dict[str, float] = Field(
        default_factory=dict,
        description="Optional normalized offsets within target zone wedge (0-1).",
    )


class GenerateLayoutRequest(BaseModel):
    payload: FloorPlanPayload
    orientations: list[RoomOrientation] | None = None
    rule_results: list[RuleEvaluationResult] | None = None
    llm_assignments: list[LLMRoomAssignment] | None = None
    export_format: LayoutExportFormat = LayoutExportFormat.vastu_layout_json
    target_compliance_score: float = 100.0
    context: dict[str, Any] = Field(default_factory=dict)


class GenerateLayoutResponse(BaseModel):
    layout: GeneratedLayoutDocument
    llm_prompt_context: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Intelligent 2D layout pipeline: VLM extract → Vastu → constrained correction → image
# ---------------------------------------------------------------------------


class UserConstraintKind(str, Enum):
    fixed_room = "fixed_room"
    fixed_zone = "fixed_zone"
    max_move = "max_move"
    preserve_room_type = "preserve_room_type"
    preserve_element = "preserve_element"


class UserLayoutConstraint(BaseModel):
    """
    User preference: keep parts of the layout unchanged during Vastu correction.

    Examples:
    - fixed_room + room_id: master bedroom stays exactly where it is
    - fixed_zone + room_id + zone: kitchen must remain in south_east
    - max_move + room_id + max_translation_feet: allow only small nudges
    """

    constraint_id: str
    kind: UserConstraintKind
    room_id: str | None = None
    room_type: str | None = None
    zone: str | None = None
    element_id: str | None = None
    max_translation_feet: float | None = None
    reason: str = ""


class ExtractedLayoutElement(BaseModel):
    id: str
    name: str
    element_type: ElementType
    polygon: list[Point2D] = Field(default_factory=list)
    confidence: float = 0.85
    source: Literal["vlm", "cad", "fusion", "manual"] = "vlm"
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayoutExtractionResult(BaseModel):
    version: str = "1.0"
    extraction_method: Literal["vlm_vision", "cad_vector", "fusion", "direct_payload"] = "direct_payload"
    model: str | None = None
    true_north_degrees: float = 0.0
    plot_boundary: list[Point2D] = Field(default_factory=list)
    elements: list[ExtractedLayoutElement] = Field(default_factory=list)
    payload: FloorPlanPayload
    confidence_score: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    raw_vlm_notes: dict[str, Any] = Field(default_factory=dict)


class ConstraintValidationResult(BaseModel):
    valid: bool
    locked_room_ids: list[str] = Field(default_factory=list)
    skipped_corrections: list[str] = Field(default_factory=list)
    violations: list[dict[str, str]] = Field(default_factory=list)
    satisfied_constraints: list[str] = Field(default_factory=list)


class LayoutImageArtifact(BaseModel):
    format: Literal["svg", "png_base64"] = "svg"
    content: str
    label: str
    width: int = 800
    height: int = 600


class LayoutImageBundle(BaseModel):
    original: LayoutImageArtifact | None = None
    corrected: LayoutImageArtifact | None = None
    comparison: LayoutImageArtifact | None = None


class IntelligentLayoutRequest(BaseModel):
    """2D layout in → extract → Vastu report → constrained perfect layout image out."""

    payload: FloorPlanPayload | None = None
    image_base64: str | None = None
    image_media_type: str = "image/png"
    true_north_degrees: float | None = None
    user_constraints: list[UserLayoutConstraint] = Field(default_factory=list)
    shift_distance_feet: float = 3.0
    generate_layout_images: bool = True
    context: dict[str, Any] = Field(default_factory=dict)


class IntelligentLayoutResponse(BaseModel):
    extraction: LayoutExtractionResult
    report: ComplianceReport
    corrected_layout: CorrectedLayoutResult | None = None
    constraint_validation: ConstraintValidationResult
    layout_images: LayoutImageBundle = Field(default_factory=lambda: LayoutImageBundle())
    pipeline_stages: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Report-driven new 2D layout generation + CAD/BIM I/O
# ---------------------------------------------------------------------------


class LayoutIoFormat(str, Enum):
    vastu_layout_json = "vastu_layout_json"
    dxf = "dxf"
    revit_json = "revit_json"
    autocad_json = "autocad_json"


class RevitLayoutRoom(BaseModel):
    id: str
    name: str
    room_type: str
    zone: str
    polygon: list[Point2D]
    area: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RevitLayoutExport(BaseModel):
    """Revit plugin import format — new Vastu-compliant 2D layout."""

    format: Literal["vastu_revit_layout_v1"] = "vastu_revit_layout_v1"
    true_north_degrees: float = 0.0
    plot_boundary: list[Point2D] = Field(default_factory=list)
    plot_center: Point2D
    rooms: list[RevitLayoutRoom] = Field(default_factory=list)
    walls: list[FloorPlanElement] = Field(default_factory=list)
    compliance_score: float
    original_compliance_score: float
    source_request_id: str | None = None
    generation_strategy: str = "report_driven"


class AutocadLayoutExport(BaseModel):
    """AutoCAD plugin import format — layers + entities blueprint."""

    format: Literal["vastu_autocad_layout_v1"] = "vastu_autocad_layout_v1"
    dxf_blueprint: dict[str, Any] = Field(default_factory=dict)
    dxf_base64: str | None = None
    filename_hint: str = "vastu_layout.dxf"
    compliance_score: float = 0.0
    original_compliance_score: float = 0.0


class LayoutIoBundle(BaseModel):
    floor_plan_payload: FloorPlanPayload
    revit: RevitLayoutExport
    autocad: AutocadLayoutExport
    layout_document: GeneratedLayoutDocument


class GenerateLayoutFromReportRequest(BaseModel):
    """Generate a new 2D Vastu-compliant layout from compliance report + original geometry."""

    payload: FloorPlanPayload
    report: ComplianceReport | None = None
    user_constraints: list[UserLayoutConstraint] = Field(default_factory=list)
    use_llm_planner: bool = True
    export_formats: list[LayoutIoFormat] = Field(
        default_factory=lambda: [
            LayoutIoFormat.vastu_layout_json,
            LayoutIoFormat.revit_json,
            LayoutIoFormat.autocad_json,
            LayoutIoFormat.dxf,
        ]
    )
    target_compliance_score: float = 95.0
    generate_svg_preview: bool = True
    context: dict[str, Any] = Field(default_factory=dict)


class GenerateLayoutFromReportResponse(BaseModel):
    layout: GeneratedLayoutDocument
    io_bundle: LayoutIoBundle
    constraint_validation: ConstraintValidationResult
    llm_assignments: list[LLMRoomAssignment] = Field(default_factory=list)
    layout_images: LayoutImageBundle = Field(default_factory=lambda: LayoutImageBundle())
    pipeline_stages: list[str] = Field(default_factory=list)


class ReportDownloadRequest(BaseModel):
    """Request a downloadable Vastu report package (HTML + JSON + visual assets)."""

    report: ComplianceReport
    project_name: str | None = None


class ReportDownloadResponse(BaseModel):
    filename: str
    html: str
    zip_base64: str
    assets: dict[str, str] = Field(default_factory=dict)
    message: str = "Report ready for download. Decode zip_base64 to save a ZIP bundle."
