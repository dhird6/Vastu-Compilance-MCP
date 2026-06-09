using System;
using System.Linq;
using System.Text;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Models;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

[Transaction(TransactionMode.Manual)]
public class AnalyzeVastuCommand : IExternalCommand
{
    public Result Execute(
        ExternalCommandData commandData,
        ref string message,
        ElementSet elements)
    {
        UIDocument? uiDocument = commandData.Application.ActiveUIDocument;
        if (uiDocument?.Document == null)
        {
            message = "No active Revit document found.";
            return Result.Failed;
        }

        Document document = uiDocument.Document;

        try
        {
            PreviewGraphicsHelper.ClearAll(document);

            RevitModelExtractor extractor = new RevitModelExtractor();
            RevitAnalyzeRequest request = extractor.BuildAnalyzeRequest(document);

            VastuApiClient client = new VastuApiClient();
            AnalyzeComplianceResponse response = client.AnalyzeRevit3D(request);

            VastuSession.SetLastReport(response.Report);

            ComplianceViewHighlighter highlighter = new ComplianceViewHighlighter();
            int highlighted = highlighter.ApplyHeatmap(
                document,
                document.ActiveView,
                response.Report);

            ComplianceReportExporter exporter = new ComplianceReportExporter();
            ExportResult export = exporter.Export(
                response.Report,
                document.ProjectInformation?.Name ?? document.Title);

            VastuSession.SetLastExportPaths(export.HtmlPath, export.JsonPath);

            ComplianceReportPresenter.ShowResultsDialog(response.Report, export);

            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Failed to run Vastu compliance analysis: " + ex.Message;
            return Result.Failed;
        }
    }

    public static string BuildSummary(ComplianceReport report)
    {
        if (report?.Summary == null)
        {
            return "No compliance report received from server.";
        }

        ComplianceSummary summary = report.Summary;
        StringBuilder builder = new StringBuilder();
        builder.AppendLine("Compliance Score: " + summary.ComplianceScore.ToString("0.00"));
        builder.AppendLine("Grade: " + summary.Grade);
        builder.AppendLine("Passed Rules: " + summary.PassedRules);
        builder.AppendLine("Failed Rules: " + summary.FailedRules);
        builder.AppendLine();

        if (report.RemediationPlan != null && !string.IsNullOrWhiteSpace(report.RemediationPlan.Summary))
        {
            builder.AppendLine("Remediation Plan:");
            builder.AppendLine(report.RemediationPlan.Summary);
            builder.AppendLine("Use Result Layout for solid corrected plan, Ghost Preview for shift arrows.");
            builder.AppendLine();
        }

        var topRecommendations = report.Recommendations?
            .Take(3)
            .Select((item, idx) =>
            {
                string references = item.ScripturalReferences != null && item.ScripturalReferences.Any()
                    ? " | Vedic Ref: " + item.ScripturalReferences.First()
                    : string.Empty;
                return (idx + 1) + ". " + item.Recommendation + references;
            }) ?? Enumerable.Empty<string>();

        builder.AppendLine("Top Recommendations:");
        builder.AppendLine(string.Join(Environment.NewLine, topRecommendations));

        return builder.ToString();
    }
}
