using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

[Transaction(TransactionMode.Manual)]
public class ClearGhostDesignCommand : IExternalCommand
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

        int count = VastuSession.GetGhostElementIds().Count;
        if (count == 0)
        {
            TaskDialog.Show("Vastu Compliance", "No ghost design preview is active.");
            return Result.Cancelled;
        }

        GhostDesignRenderer.Clear(uiDocument.Document);
        TaskDialog.Show("Vastu Compliance", $"Removed ghost preview ({count} element(s)).");
        return Result.Succeeded;
    }
}
