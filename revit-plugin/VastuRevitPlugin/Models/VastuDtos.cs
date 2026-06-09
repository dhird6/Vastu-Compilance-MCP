using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace VastuRevitPlugin.Models;

public class RevitAnalyzeRequest
{
    [JsonProperty("payload")]
    public RevitPayload Payload { get; set; } = new();

    [JsonProperty("context")]
    public Dictionary<string, object> Context { get; set; } = new();
}

public class RevitPayload
{
    [JsonProperty("source")]
    public string Source { get; set; } = "revit_3d";

    [JsonProperty("true_north_degrees")]
    public double TrueNorthDegrees { get; set; }

    [JsonProperty("levels")]
    public List<string> Levels { get; set; } = new();

    [JsonProperty("elements")]
    public List<RevitElement3D> Elements { get; set; } = new();
}

public class RevitElement3D
{
    [JsonProperty("id")]
    public string Id { get; set; } = string.Empty;

    [JsonProperty("name")]
    public string Name { get; set; } = string.Empty;

    [JsonProperty("element_type")]
    public string ElementType { get; set; } = string.Empty;

    [JsonProperty("bounding_box")]
    public BoundingBox3D BoundingBox { get; set; } = new();

    [JsonProperty("metadata")]
    public Dictionary<string, object> Metadata { get; set; } = new();
}

public class BoundingBox3D
{
    [JsonProperty("min")]
    public Point3D Min { get; set; } = new();

    [JsonProperty("max")]
    public Point3D Max { get; set; } = new();
}

public class Point3D
{
    [JsonProperty("x")]
    public double X { get; set; }

    [JsonProperty("y")]
    public double Y { get; set; }

    [JsonProperty("z")]
    public double Z { get; set; }
}

public class AnalyzeComplianceResponse
{
    [JsonProperty("report")]
    public ComplianceReport Report { get; set; } = new();
}

public class ComplianceReport
{
    [JsonProperty("request_id")]
    public string RequestId { get; set; } = string.Empty;

    [JsonProperty("summary")]
    public ComplianceSummary Summary { get; set; } = new();

    [JsonProperty("recommendations")]
    public List<AIRecommendation> Recommendations { get; set; } = new();

    [JsonProperty("remediation_plan")]
    public RemediationPlan RemediationPlan { get; set; } = new();

    [JsonProperty("corrected_layout")]
    public CorrectedLayoutResult? CorrectedLayout { get; set; }

    [JsonProperty("rule_results")]
    public List<RuleEvaluationResult> RuleResults { get; set; } = new();

    [JsonProperty("orientations")]
    public List<RoomOrientationDto> Orientations { get; set; } = new();

    [JsonProperty("heatmap")]
    public List<HeatmapCell> Heatmap { get; set; } = new();

    [JsonProperty("structured_output")]
    public JObject? StructuredOutput { get; set; }

    [JsonProperty("html_report")]
    public string? HtmlReport { get; set; }
}

public class ComplianceSummary
{
    [JsonProperty("compliance_score")]
    public double ComplianceScore { get; set; }

    [JsonProperty("grade")]
    public string Grade { get; set; } = string.Empty;

    [JsonProperty("passed_rules")]
    public int PassedRules { get; set; }

    [JsonProperty("failed_rules")]
    public int FailedRules { get; set; }

    [JsonProperty("total_rooms")]
    public int TotalRooms { get; set; }
}

public class RoomOrientationDto
{
    [JsonProperty("room_id")]
    public string RoomId { get; set; } = string.Empty;

    [JsonProperty("room_name")]
    public string RoomName { get; set; } = string.Empty;

    [JsonProperty("room_type")]
    public string RoomType { get; set; } = string.Empty;

    [JsonProperty("zone")]
    public string Zone { get; set; } = string.Empty;

    [JsonProperty("area")]
    public double Area { get; set; }

    [JsonProperty("orientation_degrees")]
    public double OrientationDegrees { get; set; }
}

public class HeatmapCell
{
    [JsonProperty("room_id")]
    public string RoomId { get; set; } = string.Empty;

    [JsonProperty("zone")]
    public string Zone { get; set; } = string.Empty;

    [JsonProperty("score")]
    public double Score { get; set; }

    [JsonProperty("color_hex")]
    public string ColorHex { get; set; } = "#9ACD32";

    [JsonProperty("status")]
    public string Status { get; set; } = "compliant";
}

public class AIRecommendation
{
    [JsonProperty("room_id")]
    public string RoomId { get; set; } = string.Empty;

    [JsonProperty("recommendation")]
    public string Recommendation { get; set; } = string.Empty;

    [JsonProperty("rationale")]
    public string Rationale { get; set; } = string.Empty;

    [JsonProperty("scriptural_references")]
    public List<string> ScripturalReferences { get; set; } = new();
}

public class RuleEvaluationResult
{
    [JsonProperty("rule_id")]
    public string RuleId { get; set; } = string.Empty;

    [JsonProperty("title")]
    public string Title { get; set; } = string.Empty;

    [JsonProperty("passed")]
    public bool Passed { get; set; }

    [JsonProperty("room_id")]
    public string RoomId { get; set; } = string.Empty;

    [JsonProperty("zone")]
    public string Zone { get; set; } = string.Empty;

    [JsonProperty("expected_zones")]
    public List<string> ExpectedZones { get; set; } = new();

    [JsonProperty("explanation")]
    public string Explanation { get; set; } = string.Empty;

    [JsonProperty("severity")]
    public string Severity { get; set; } = "medium";
}

public class RemediationPlan
{
    [JsonProperty("summary")]
    public string Summary { get; set; } = string.Empty;

    [JsonProperty("auto_applicable_count")]
    public int AutoApplicableCount { get; set; }

    [JsonProperty("manual_approval_count")]
    public int ManualApprovalCount { get; set; }

    [JsonProperty("actions")]
    public List<RemediationAction> Actions { get; set; } = new();
}

public class RemediationAction
{
    [JsonProperty("action_id")]
    public string ActionId { get; set; } = string.Empty;

    [JsonProperty("room_id")]
    public string RoomId { get; set; } = string.Empty;

    [JsonProperty("rule_id")]
    public string RuleId { get; set; } = string.Empty;

    [JsonProperty("action_type")]
    public string ActionType { get; set; } = string.Empty;

    [JsonProperty("description")]
    public string Description { get; set; } = string.Empty;

    [JsonProperty("parameters")]
    public Dictionary<string, object> Parameters { get; set; } = new();

    [JsonProperty("requires_user_approval")]
    public bool RequiresUserApproval { get; set; }

    [JsonProperty("auto_applicable")]
    public bool AutoApplicable { get; set; }
}

public class CorrectedLayoutResult
{
    [JsonProperty("version")]
    public string Version { get; set; } = "1.0";

    [JsonProperty("approach")]
    public string Approach { get; set; } = "same_layout_with_suggestions";

    [JsonProperty("original_source")]
    public string OriginalSource { get; set; } = string.Empty;

    [JsonProperty("corrected_payload")]
    public CorrectedFloorPlanPayload CorrectedPayload { get; set; } = new();

    [JsonProperty("changes_applied")]
    public List<AppliedLayoutChange> ChangesApplied { get; set; } = new();

    [JsonProperty("original_compliance_score")]
    public double OriginalComplianceScore { get; set; }

    [JsonProperty("corrected_compliance_score")]
    public double CorrectedComplianceScore { get; set; }

    [JsonProperty("compliance_improved")]
    public bool ComplianceImproved { get; set; }
}

public class AppliedLayoutChange
{
    [JsonProperty("room_id")]
    public string RoomId { get; set; } = string.Empty;

    [JsonProperty("room_name")]
    public string RoomName { get; set; } = string.Empty;

    [JsonProperty("original_zone")]
    public string OriginalZone { get; set; } = string.Empty;

    [JsonProperty("target_zone")]
    public string TargetZone { get; set; } = string.Empty;

    [JsonProperty("corrected_zone")]
    public string CorrectedZone { get; set; } = string.Empty;

    [JsonProperty("translation")]
    public Dictionary<string, object> Translation { get; set; } = new();
}

public class CorrectedFloorPlanPayload
{
    [JsonProperty("source")]
    public string Source { get; set; } = "vastu_corrected_2d";

    [JsonProperty("true_north_degrees")]
    public double TrueNorthDegrees { get; set; }

    [JsonProperty("elements")]
    public List<FloorPlanElementDto> Elements { get; set; } = new();
}

public class FloorPlanElementDto
{
    [JsonProperty("id")]
    public string Id { get; set; } = string.Empty;

    [JsonProperty("name")]
    public string Name { get; set; } = string.Empty;

    [JsonProperty("element_type")]
    public string ElementType { get; set; } = string.Empty;

    [JsonProperty("polygon")]
    public List<Point2DDto> Polygon { get; set; } = new();

    [JsonProperty("metadata")]
    public Dictionary<string, object> Metadata { get; set; } = new();
}

public class Point2DDto
{
    [JsonProperty("x")]
    public double X { get; set; }

    [JsonProperty("y")]
    public double Y { get; set; }
}

public class FloorPlanPayloadDto
{
    [JsonProperty("source")]
    public string Source { get; set; } = "direct_json";

    [JsonProperty("true_north_degrees")]
    public double TrueNorthDegrees { get; set; }

    [JsonProperty("elements")]
    public List<FloorPlanElementDto> Elements { get; set; } = new();
}

public class GenerateLayoutFromReportRequest
{
    [JsonProperty("payload")]
    public FloorPlanPayloadDto Payload { get; set; } = new();

    [JsonProperty("report")]
    public ComplianceReport? Report { get; set; }

    [JsonProperty("user_constraints")]
    public List<UserLayoutConstraintDto> UserConstraints { get; set; } = new();

    [JsonProperty("use_llm_planner")]
    public bool UseLlmPlanner { get; set; } = true;

    [JsonProperty("generate_svg_preview")]
    public bool GenerateSvgPreview { get; set; } = false;
}

public class GenerateLayoutFromReportResponse
{
    [JsonProperty("layout")]
    public GeneratedLayoutDocumentDto Layout { get; set; } = new();

    [JsonProperty("io_bundle")]
    public LayoutIoBundleDto IoBundle { get; set; } = new();
}

public class LayoutIoBundleDto
{
    [JsonProperty("revit")]
    public RevitLayoutExportDto Revit { get; set; } = new();

    [JsonProperty("autocad")]
    public AutocadLayoutExportDto Autocad { get; set; } = new();
}

public class RevitLayoutExportDto
{
    [JsonProperty("format")]
    public string Format { get; set; } = string.Empty;

    [JsonProperty("true_north_degrees")]
    public double TrueNorthDegrees { get; set; }

    [JsonProperty("plot_boundary")]
    public List<Point2DDto> PlotBoundary { get; set; } = new();

    [JsonProperty("plot_center")]
    public Point2DDto PlotCenter { get; set; } = new();

    [JsonProperty("rooms")]
    public List<RevitLayoutRoomDto> Rooms { get; set; } = new();

    [JsonProperty("compliance_score")]
    public double ComplianceScore { get; set; }

    [JsonProperty("original_compliance_score")]
    public double OriginalComplianceScore { get; set; }
}

public class RevitLayoutRoomDto
{
    [JsonProperty("id")]
    public string Id { get; set; } = string.Empty;

    [JsonProperty("name")]
    public string Name { get; set; } = string.Empty;

    [JsonProperty("room_type")]
    public string RoomType { get; set; } = string.Empty;

    [JsonProperty("zone")]
    public string Zone { get; set; } = string.Empty;

    [JsonProperty("polygon")]
    public List<Point2DDto> Polygon { get; set; } = new();

    [JsonProperty("area")]
    public double Area { get; set; }
}

public class AutocadLayoutExportDto
{
    [JsonProperty("format")]
    public string Format { get; set; } = string.Empty;

    [JsonProperty("dxf_blueprint")]
    public Dictionary<string, object> DxfBlueprint { get; set; } = new();

    [JsonProperty("dxf_base64")]
    public string? DxfBase64 { get; set; }

    [JsonProperty("filename_hint")]
    public string FilenameHint { get; set; } = "vastu_layout.dxf";

    [JsonProperty("compliance_score")]
    public double ComplianceScore { get; set; }

    [JsonProperty("original_compliance_score")]
    public double OriginalComplianceScore { get; set; }
}

public class UserLayoutConstraintDto
{
    [JsonProperty("constraint_id")]
    public string ConstraintId { get; set; } = string.Empty;

    [JsonProperty("kind")]
    public string Kind { get; set; } = string.Empty;

    [JsonProperty("room_id")]
    public string? RoomId { get; set; }

    [JsonProperty("room_type")]
    public string? RoomType { get; set; }

    [JsonProperty("zone")]
    public string? Zone { get; set; }

    [JsonProperty("max_translation_feet")]
    public double? MaxTranslationFeet { get; set; }

    [JsonProperty("reason")]
    public string Reason { get; set; } = string.Empty;
}

public class GeneratedLayoutDocumentDto
{
    [JsonProperty("metadata")]
    public GeneratedLayoutMetadataDto Metadata { get; set; } = new();

    [JsonProperty("rooms")]
    public List<RevitLayoutRoomDto> Rooms { get; set; } = new();
}

public class GeneratedLayoutMetadataDto
{
    [JsonProperty("generated_compliance_score")]
    public double GeneratedComplianceScore { get; set; }

    [JsonProperty("original_compliance_score")]
    public double OriginalComplianceScore { get; set; }

    [JsonProperty("generation_strategy")]
    public string GenerationStrategy { get; set; } = string.Empty;
}

