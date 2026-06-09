using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Models;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

[Transaction(TransactionMode.Manual)]
public class ExportGeneratedLayoutCommand : IExternalCommand
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
        GenerateLayoutFromReportResponse? generated = VastuSession.GetLastGeneratedLayout();
        if (generated?.IoBundle?.Autocad == null)
        {
            TaskDialog.Show("Export Layout", "No generated layout available. Run 'Generate Layout' first.");
            return Result.Cancelled;
        }

        try
        {
            string projectName = document.ProjectInformation?.Name ?? document.Title ?? "revit_project";
            string path = LayoutDxfFileExporter.ExportToDocuments(generated.IoBundle.Autocad, projectName);
            VastuSession.SetLastExportedDxfPath(path);
            TaskDialog.Show("Export Layout", "DXF exported to:\n" + path);
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Failed to export generated layout: " + ex.Message;
            return Result.Failed;
        }
    }
}
