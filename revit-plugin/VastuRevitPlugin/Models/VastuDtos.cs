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
