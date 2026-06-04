using System;
using System.Linq;
using System.Text;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using VastuRevitPlugin.Commands;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Builds rich TaskDialog output from structured MCP report.
/// </summary>
public static class ComplianceReportPresenter
{
    public static void ShowResultsDialog(ComplianceReport report, ExportResult? export = null)
    {
        TaskDialog dialog = new TaskDialog("Vastu Compliance Report");

        JObject? structured = report.StructuredOutput;
        if (structured?["executive_summary"] is JObject exec)
        {
            dialog.MainInstruction = exec["headline"]?.ToString() ?? "Vastu analysis complete";
            dialog.MainContent = BuildMainContent(exec, report.Summary);
            dialog.ExpandedContent = BuildExpandedContent(structured, report);
        }
        else
        {
            dialog.MainInstruction = "Vastu analysis complete";
            dialog.MainContent = AnalyzeVastuCommand.BuildSummary(report);
        }

        if (export != null && export.Success)
        {
            dialog.FooterText = "HTML report: " + export.HtmlPath;
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, "Open HTML report in browser");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, "Open reports folder");

            TaskDialogResult result = dialog.Show();
            if (result == TaskDialogResult.CommandLink1)
            {
                ReportLauncher.OpenFile(export.HtmlPath);
            }
            else if (result == TaskDialogResult.CommandLink2)
            {
                ReportLauncher.OpenFolder(export.Folder);
            }
            return;
        }

        dialog.Show();
    }

    private static string BuildMainContent(JObject exec, ComplianceSummary summary)
    {
        StringBuilder sb = new StringBuilder();
        sb.AppendLine($"Score: {summary.ComplianceScore:0.0}%  ·  Grade {summary.Grade}");
        sb.AppendLine($"Rooms: {summary.TotalRooms}  ·  Passed: {summary.PassedRules}  ·  Failed: {summary.FailedRules}");
        sb.AppendLine($"Auto fixes: {exec["auto_fixes"]}  ·  Manual: {exec["manual_fixes"]}");
        sb.AppendLine();
        sb.AppendLine("View: color-coded rooms in plan (heatmap applied).");
        sb.AppendLine("Next: Ghost Preview → Apply Remediation");
        return sb.ToString();
    }

    private static string BuildExpandedContent(JObject structured, ComplianceReport report)
    {
        StringBuilder sb = new StringBuilder();
        if (structured["priority_fixes"] is JArray fixes)
        {
            sb.AppendLine("Priority fixes:");
            foreach (JToken fix in fixes.Take(8))
            {
                string room = fix["room_name"]?.ToString() ?? "";
                string rule = fix["rule_id"]?.ToString() ?? "";
                string current = fix["current_zone"]?.ToString() ?? "";
                string target = fix["target_zone"]?.ToString() ?? "";
                string sanskrit = fix["target_sanskrit"]?.ToString() ?? "";
                sb.AppendLine($"  • {room}: {current} → {target} ({sanskrit}) [{rule}]");
            }
            sb.AppendLine();
        }

        if (!string.IsNullOrWhiteSpace(report.RemediationPlan?.Summary))
        {
            sb.AppendLine(report.RemediationPlan.Summary);
        }

        return sb.ToString();
    }
}

public static class ReportLauncher
{
    public static void OpenFile(string path)
    {
        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = path,
                UseShellExecute = true,
            });
        }
        catch
        {
            // Ignore launch failures
        }
    }

    public static void OpenFolder(string folder)
    {
        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = folder,
                UseShellExecute = true,
            });
        }
        catch
        {
            // Ignore launch failures
        }
    }
}
