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
        [JsonProperty("summary")]
        public ComplianceSummary Summary { get; set; }

        [JsonProperty("recommendations")]
        public List<Recommendation> Recommendations { get; set; } = new List<Recommendation>();
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
}
