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
/// Unified bridge: applies RemediationPlan from MCP — safe fixes, guides, and geometry moves.
/// </summary>
[Transaction(TransactionMode.Manual)]
public class ApplyRemediationCommand : IExternalCommand
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
        int safeCount = RemediationExecutor.CountSafeActions(plan);
        int geometryCount = RemediationExecutor.CountGeometryActions(plan);

        var intro = new StringBuilder();
        intro.AppendLine(plan.Summary);
        intro.AppendLine();
        intro.AppendLine($"Safe actions: {safeCount}");
        intro.AppendLine($"Geometry moves: {geometryCount}");
        intro.AppendLine();
        intro.AppendLine("This command will:");
        intro.AppendLine("1) Apply safe fixes (highlights, tags, zone guides)");
        if (geometryCount > 0)
        {
            intro.AppendLine("2) Ask approval, then move room boundary walls toward Vastu zones");
        }

        TaskDialogResult start = TaskDialog.Show(
            "Apply Vastu Remediation Plan",
            intro.ToString(),
            TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No);

        if (start != TaskDialogResult.Yes)
        {
            return Result.Cancelled;
        }

        try
        {
            RemediationExecutor executor = new RemediationExecutor();
            var combined = new RemediationApplyResult();

            RemediationApplyResult safeResult = executor.Apply(
                uiDocument.Document,
                plan,
                RemediationApplyMode.SafeOnly);
            MergeResults(combined, safeResult);

            if (geometryCount > 0)
            {
                TaskDialogResult geometryConfirm = TaskDialog.Show(
                    "Apply Geometry Alignment",
                    "Move non-compliant room boundary walls toward target Vastu zones?\n\n" +
                    "This modifies your home model geometry. Use Undo (Ctrl+Z) if needed.\n\n" +
                    "Recommended: work on a copy of the project first.",
                    TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No);

                if (geometryConfirm == TaskDialogResult.Yes)
                {
                    RemediationApplyResult geometryResult = executor.Apply(
                        uiDocument.Document,
                        plan,
                        RemediationApplyMode.GeometryOnly);
                    MergeResults(combined, geometryResult);
                }
                else
                {
                    combined.Messages.Add("Geometry moves skipped by user.");
                }
            }

            StringBuilder summary = new StringBuilder();
            summary.AppendLine("Remediation plan applied.");
            summary.AppendLine(combined.Summary);
            if (combined.Messages.Any())
            {
                summary.AppendLine();
                summary.AppendLine(string.Join(Environment.NewLine, combined.Messages.Take(8)));
            }

            summary.AppendLine();
            summary.AppendLine("Re-run Analyze Vastu to verify updated compliance.");

            TaskDialog.Show("Vastu Remediation", summary.ToString());
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Failed to apply remediation plan: " + ex.Message;
            return Result.Failed;
        }
    }

    private static void MergeResults(RemediationApplyResult target, RemediationApplyResult source)
    {
        target.AppliedCount += source.AppliedCount;
        target.SkippedCount += source.SkippedCount;
        target.FailedCount += source.FailedCount;
        target.Messages.AddRange(source.Messages);
    }
}
