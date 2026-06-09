using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Models;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

[Transaction(TransactionMode.Manual)]
public class ShowGeneratedLayoutCommand : IExternalCommand
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
        View? view = document.ActiveView;

        GenerateLayoutFromReportResponse? generated = VastuSession.GetLastGeneratedLayout();
        if (generated?.IoBundle?.Revit == null)
        {
            TaskDialog.Show("Vastu Layout", "No generated layout available. Run 'Generate Layout' first.");
            return Result.Cancelled;
        }

        try
        {
            ResultRenderResult result = new GeneratedLayoutRenderer().Show(
                document,
                view,
                generated.IoBundle.Revit);

            if (!result.Success)
            {
                message = result.Message;
                return Result.Failed;
            }

            TaskDialog.Show("Vastu Generated Layout", result.Message);
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Failed to show generated layout: " + ex.Message;
            return Result.Failed;
        }
    }
}
