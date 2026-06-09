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

        int ghostCount = VastuSession.GetGhostElementIds().Count;
        int resultCount = VastuSession.GetResultElementIds().Count;
        if (ghostCount == 0 && resultCount == 0)
        {
            TaskDialog.Show("Vastu Compliance", "No preview graphics are active (ghost or result layout).");
            return Result.Cancelled;
        }

        Document document = uiDocument.Document;
        PreviewGraphicsHelper.ClearAll(document);

        TaskDialog.Show(
            "Vastu Compliance",
            $"Removed preview graphics: {ghostCount} ghost + {resultCount} result element(s).");
        return Result.Succeeded;
    }
}
