using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services.Abstractions
{
    /// <summary>
    /// HTTP client abstraction for Vastu Compliance MCP server.
    /// </summary>
    public interface IVastuApiClient
    {
        AnalyzeComplianceResponse AnalyzeAutocadLayout(AnalyzeAutocadRequest request);

        GenerateLayoutFromReportResponse GenerateLayoutFromReport(GenerateLayoutFromReportRequest request);
    }
}
