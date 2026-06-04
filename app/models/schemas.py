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
    source: Literal["aps", "direct_json", "revit_3d_projection"] = "direct_json"
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


class ComplianceReport(BaseModel):
    request_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: ComplianceSummary
    validation_issues: list[GeometryValidationIssue]
    orientations: list[RoomOrientation]
    rule_results: list[RuleEvaluationResult]
    recommendations: list[AIRecommendation]
    remediation_plan: RemediationPlan = Field(default_factory=lambda: RemediationPlan())
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
