using System;
using System.Linq;
using System.Text;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Models;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

/// <summary>
/// Shows ghost design preview (proposed room layout) plus remediation action summary.
/// </summary>
[Transaction(TransactionMode.Manual)]
public class PreviewVastuCommand : IExternalCommand
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

        ComplianceReport? report = VastuSession.GetLastReport();
        if (report?.RemediationPlan == null || report.RemediationPlan.Actions.Count == 0)
        {
            TaskDialog.Show(
                "Vastu Compliance",
                "No remediation plan available. Run Analyze Vastu first.");
            return Result.Cancelled;
        }

        RemediationPlan plan = report.RemediationPlan;
        StringBuilder builder = new StringBuilder();

        try
        {
            GhostDesignRenderer renderer = new GhostDesignRenderer();
            GhostRenderResult ghostResult = renderer.Show(
                uiDocument.Document,
                uiDocument.Document.ActiveView,
                plan);

            builder.AppendLine(ghostResult.Message);
            builder.AppendLine();
        }
        catch (Exception ex)
        {
            builder.AppendLine("Ghost preview failed: " + ex.Message);
            builder.AppendLine();
        }

        builder.AppendLine(plan.Summary);
        builder.AppendLine();
        builder.AppendLine("Actions (first 10):");
        foreach (RemediationAction action in plan.Actions.Take(10))
        {
            string mode = action.ActionType switch
            {
                "show_ghost_design" => "GHOST",
                "move_room_boundaries" => "WALL-MOVE",
                "draw_zone_guide" => "GUIDE",
                _ when action.AutoApplicable => "AUTO",
                _ => "MANUAL",
            };

            builder.AppendLine("- [" + mode + "] " + action.Description);
        }

        builder.AppendLine();
        builder.AppendLine("Cyan ghost outlines = proposed layout after remediation.");
        builder.AppendLine("Use Apply Remediation to apply real changes, or Clear Ghost to remove preview.");

        TaskDialog.Show("Vastu Ghost Design Preview", builder.ToString());
        return Result.Succeeded;
    }
}
