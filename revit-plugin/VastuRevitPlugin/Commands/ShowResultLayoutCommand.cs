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
/// Shows solid result layout from corrected_payload (same 2D plan with suggestions applied).
/// </summary>
[Transaction(TransactionMode.Manual)]
public class ShowResultLayoutCommand : IExternalCommand
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
        CorrectedLayoutResult? corrected = report?.CorrectedLayout;
        if (corrected?.CorrectedPayload?.Elements == null || corrected.CorrectedPayload.Elements.Count == 0)
        {
            TaskDialog.Show(
                "Vastu Compliance",
                "No corrected layout available. Run Analyze Vastu first (violations required for suggestions).");
            return Result.Cancelled;
        }

        StringBuilder builder = new StringBuilder();

        try
        {
            ResultLayoutRenderer renderer = new ResultLayoutRenderer();
            ResultRenderResult result = renderer.Show(
                uiDocument.Document,
                uiDocument.Document.ActiveView,
                corrected);

            builder.AppendLine(result.Message);
            builder.AppendLine();

            if (corrected.ChangesApplied.Count > 0)
            {
                builder.AppendLine("Rooms updated:");
                foreach (AppliedLayoutChange change in corrected.ChangesApplied.Take(8))
                {
                    builder.AppendLine(
                        $"- {change.RoomName}: {change.OriginalZone} → {change.CorrectedZone}");
                }
            }
            else
            {
                builder.AppendLine("No room moves were required — layout unchanged.");
            }

            builder.AppendLine();
            builder.AppendLine("Green solid outlines = result layout (suggestions applied).");
            builder.AppendLine("Use Ghost Preview for before/after arrows, or Clear Preview to remove.");

            TaskDialog.Show(
                result.Success ? "Vastu Result Layout" : "Vastu Result Layout — Warning",
                builder.ToString());

            return result.Success ? Result.Succeeded : Result.Failed;
        }
        catch (Exception ex)
        {
            message = "Failed to show result layout: " + ex.Message;
            return Result.Failed;
        }
    }
}
