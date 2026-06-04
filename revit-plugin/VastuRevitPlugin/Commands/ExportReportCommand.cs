using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Models;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

[Transaction(TransactionMode.ReadOnly)]
public class ExportReportCommand : IExternalCommand
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
        if (report == null)
        {
            TaskDialog.Show("Vastu Compliance", "Run Analyze Vastu first.");
            return Result.Cancelled;
        }

        ExportResult export = new ComplianceReportExporter().Export(
            report,
            uiDocument.Document.ProjectInformation?.Name);

        if (!export.Success)
        {
            message = export.Message;
            return Result.Failed;
        }

        VastuSession.SetLastExportPaths(export.HtmlPath, export.JsonPath);
        ComplianceReportPresenter.ShowResultsDialog(report, export);
        return Result.Succeeded;
    }
}
