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
public class ApplyVastuCommand : IExternalCommand
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

        TaskDialogResult confirm = TaskDialog.Show(
            "Apply Safe Fixes",
            "Apply auto-applicable fixes (highlights, comments, zone guides)?\n\n" +
            "For full plan including wall moves, use Apply Remediation Plan.",
            TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No);

        if (confirm != TaskDialogResult.Yes)
        {
            return Result.Cancelled;
        }

        try
        {
            RemediationExecutor executor = new RemediationExecutor();
            RemediationApplyResult result = executor.Apply(
                uiDocument.Document,
                report.RemediationPlan,
                RemediationApplyMode.SafeOnly);

            StringBuilder builder = new StringBuilder();
            builder.AppendLine(result.Summary);
            if (result.Messages.Any())
            {
                builder.AppendLine();
                builder.AppendLine(string.Join(Environment.NewLine, result.Messages.Take(5)));
            }

            builder.AppendLine();
            builder.AppendLine("Use Apply Remediation Plan for geometry wall moves.");

            TaskDialog.Show("Vastu Safe Fixes", builder.ToString());
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Failed to apply safe fixes: " + ex.Message;
            return Result.Failed;
        }
    }
}
