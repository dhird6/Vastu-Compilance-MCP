using System.Collections.Generic;
using Newtonsoft.Json;

namespace VastuAutoCADPlugin.Models
{
    public class AnalyzeAutocadRequest
    {
        [JsonProperty("payload")]
        public AutocadPayload Payload { get; set; }

        [JsonProperty("context")]
        public Dictionary<string, object> Context { get; set; }
    }

    public class AutocadPayload
    {
        [JsonProperty("source")]
        public string Source { get; set; } = "autocad_layout_2d";

        [JsonProperty("true_north_degrees")]
        public double TrueNorthDegrees { get; set; }

        [JsonProperty("layout_name")]
        public string LayoutName { get; set; } = "Model";

        [JsonProperty("levels")]
        public List<string> Levels { get; set; } = new List<string>();

        [JsonProperty("entities")]
        public List<AutocadEntity2D> Entities { get; set; } = new List<AutocadEntity2D>();
    }

    public class AutocadEntity2D
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("entity_type")]
        public string EntityType { get; set; }

        [JsonProperty("points")]
        public List<Point2D> Points { get; set; } = new List<Point2D>();

        [JsonProperty("metadata")]
        public Dictionary<string, object> Metadata { get; set; } = new Dictionary<string, object>();
    }

    public class Point2D
    {
        [JsonProperty("x")]
        public double X { get; set; }

        [JsonProperty("y")]
        public double Y { get; set; }
    }

    public class AnalyzeComplianceResponse
    {
        [JsonProperty("report")]
        public ComplianceReport Report { get; set; }
    }

    public class ComplianceReport
    {
        [JsonProperty("request_id")]
        public string RequestId { get; set; }

        [JsonProperty("summary")]
        public ComplianceSummary Summary { get; set; }

        [JsonProperty("recommendations")]
        public List<Recommendation> Recommendations { get; set; } = new List<Recommendation>();

        [JsonProperty("remediation_plan")]
        public RemediationPlan RemediationPlan { get; set; }

        [JsonProperty("corrected_layout")]
        public CorrectedLayoutResult CorrectedLayout { get; set; }

        [JsonProperty("html_report")]
        public string HtmlReport { get; set; }
    }

    public class RemediationPlan
    {
        [JsonProperty("summary")]
        public string Summary { get; set; }
    }

    public class ComplianceSummary
    {
        [JsonProperty("compliance_score")]
        public double ComplianceScore { get; set; }

        [JsonProperty("grade")]
        public string Grade { get; set; }

        [JsonProperty("passed_rules")]
        public int PassedRules { get; set; }

        [JsonProperty("failed_rules")]
        public int FailedRules { get; set; }
    }

    public class Recommendation
    {
        [JsonProperty("recommendation")]
        public string Text { get; set; }

        [JsonProperty("scriptural_references")]
        public List<string> ScripturalReferences { get; set; } = new List<string>();
    }

    public class CorrectedLayoutResult
    {
        [JsonProperty("approach")]
        public string Approach { get; set; }

        [JsonProperty("corrected_payload")]
        public CorrectedFloorPlanPayload CorrectedPayload { get; set; }

        [JsonProperty("changes_applied")]
        public List<AppliedLayoutChange> ChangesApplied { get; set; } = new List<AppliedLayoutChange>();

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
        public string RoomId { get; set; }

        [JsonProperty("room_name")]
        public string RoomName { get; set; }

        [JsonProperty("original_zone")]
        public string OriginalZone { get; set; }

        [JsonProperty("corrected_zone")]
        public string CorrectedZone { get; set; }
    }

    public class CorrectedFloorPlanPayload
    {
        [JsonProperty("source")]
        public string Source { get; set; }

        [JsonProperty("elements")]
        public List<FloorPlanElementDto> Elements { get; set; } = new List<FloorPlanElementDto>();
    }

    public class FloorPlanElementDto
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("element_type")]
        public string ElementType { get; set; }

        [JsonProperty("polygon")]
        public List<Point2D> Polygon { get; set; } = new List<Point2D>();

        [JsonProperty("metadata")]
        public Dictionary<string, object> Metadata { get; set; } = new Dictionary<string, object>();
    }

    public class FloorPlanPayloadDto
    {
        [JsonProperty("source")]
        public string Source { get; set; } = "direct_json";

        [JsonProperty("true_north_degrees")]
        public double TrueNorthDegrees { get; set; }

        [JsonProperty("elements")]
        public List<FloorPlanElementDto> Elements { get; set; } = new List<FloorPlanElementDto>();
    }

    public class GenerateLayoutFromReportRequest
    {
        [JsonProperty("payload")]
        public FloorPlanPayloadDto Payload { get; set; }

        [JsonProperty("report")]
        public ComplianceReport Report { get; set; }

        [JsonProperty("user_constraints")]
        public List<UserLayoutConstraintDto> UserConstraints { get; set; } = new List<UserLayoutConstraintDto>();

        [JsonProperty("use_llm_planner")]
        public bool UseLlmPlanner { get; set; } = true;

        [JsonProperty("generate_svg_preview")]
        public bool GenerateSvgPreview { get; set; } = false;
    }

    public class GenerateLayoutFromReportResponse
    {
        [JsonProperty("layout")]
        public GeneratedLayoutDocument Layout { get; set; }

        [JsonProperty("io_bundle")]
        public LayoutIoBundle IoBundle { get; set; }
    }

    public class LayoutIoBundle
    {
        [JsonProperty("revit")]
        public RevitLayoutExport Revit { get; set; }

        [JsonProperty("autocad")]
        public AutocadLayoutExport Autocad { get; set; }
    }

    public class RevitLayoutExport
    {
        [JsonProperty("format")]
        public string Format { get; set; }

        [JsonProperty("true_north_degrees")]
        public double TrueNorthDegrees { get; set; }

        [JsonProperty("plot_boundary")]
        public List<Point2D> PlotBoundary { get; set; } = new List<Point2D>();

        [JsonProperty("plot_center")]
        public Point2D PlotCenter { get; set; }

        [JsonProperty("rooms")]
        public List<RevitLayoutRoom> Rooms { get; set; } = new List<RevitLayoutRoom>();

        [JsonProperty("compliance_score")]
        public double ComplianceScore { get; set; }

        [JsonProperty("original_compliance_score")]
        public double OriginalComplianceScore { get; set; }
    }

    public class RevitLayoutRoom
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("room_type")]
        public string RoomType { get; set; }

        [JsonProperty("zone")]
        public string Zone { get; set; }

        [JsonProperty("polygon")]
        public List<Point2D> Polygon { get; set; } = new List<Point2D>();

        [JsonProperty("area")]
        public double Area { get; set; }
    }

    public class AutocadLayoutExport
    {
        [JsonProperty("format")]
        public string Format { get; set; }

        [JsonProperty("dxf_blueprint")]
        public DxfBlueprint DxfBlueprint { get; set; }

        [JsonProperty("dxf_base64")]
        public string DxfBase64 { get; set; }

        [JsonProperty("filename_hint")]
        public string FilenameHint { get; set; }

        [JsonProperty("compliance_score")]
        public double ComplianceScore { get; set; }

        [JsonProperty("original_compliance_score")]
        public double OriginalComplianceScore { get; set; }
    }

    public class UserLayoutConstraintDto
    {
        [JsonProperty("constraint_id")]
        public string ConstraintId { get; set; }

        [JsonProperty("kind")]
        public string Kind { get; set; }

        [JsonProperty("room_id")]
        public string RoomId { get; set; }

        [JsonProperty("room_type")]
        public string RoomType { get; set; }

        [JsonProperty("zone")]
        public string Zone { get; set; }

        [JsonProperty("max_translation_feet")]
        public double? MaxTranslationFeet { get; set; }

        [JsonProperty("reason")]
        public string Reason { get; set; }
    }

    public class DxfBlueprint
    {
        [JsonProperty("layers")]
        public Dictionary<string, DxfLayer> Layers { get; set; } = new Dictionary<string, DxfLayer>();

        [JsonProperty("entities")]
        public List<DxfEntity> Entities { get; set; } = new List<DxfEntity>();
    }

    public class DxfLayer
    {
        [JsonProperty("color")]
        public int Color { get; set; }
    }

    public class DxfEntity
    {
        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("layer")]
        public string Layer { get; set; }

        [JsonProperty("points")]
        public List<Point2D> Points { get; set; }

        [JsonProperty("closed")]
        public bool Closed { get; set; }

        [JsonProperty("start")]
        public Point2D Start { get; set; }

        [JsonProperty("end")]
        public Point2D End { get; set; }
    }

    public class GeneratedLayoutDocument
    {
        [JsonProperty("metadata")]
        public GeneratedLayoutMetadata Metadata { get; set; }

        [JsonProperty("rooms")]
        public List<RevitLayoutRoom> Rooms { get; set; } = new List<RevitLayoutRoom>();
    }

    public class GeneratedLayoutMetadata
    {
        [JsonProperty("generated_compliance_score")]
        public double GeneratedComplianceScore { get; set; }

        [JsonProperty("original_compliance_score")]
        public double OriginalComplianceScore { get; set; }

        [JsonProperty("generation_strategy")]
        public string GenerationStrategy { get; set; }
    }
}
