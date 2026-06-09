using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using VastuRevitPlugin.Models;
using VastuRevitPlugin.Services;

namespace VastuRevitPlugin.Commands;

[Transaction(TransactionMode.Manual)]
public class GenerateVastuLayoutCommand : IExternalCommand
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

        try
        {
            GeneratedLayoutRenderer.Clear(document);

            RevitModelExtractor extractor = new RevitModelExtractor();
            FloorPlanPayloadDto payload = extractor.BuildFloorPlanPayload(document);
            if (payload.Elements.Count == 0)
            {
                TaskDialog.Show("Vastu Layout", "No room boundaries found. Place and boundary rooms first.");
                return Result.Cancelled;
            }

            ComplianceReport? report = VastuSession.GetLastReport();
            IReadOnlyList<UserLayoutConstraintDto> constraints = VastuSession.GetLayoutConstraints();
            var request = new GenerateLayoutFromReportRequest
            {
                Payload = payload,
                Report = report,
                UserConstraints = constraints.ToList(),
                UseLlmPlanner = true,
                GenerateSvgPreview = false
            };

            VastuApiClient client = new VastuApiClient();
            GenerateLayoutFromReportResponse response = client.GenerateLayoutFromReport(request);
            VastuSession.SetLastGeneratedLayout(response);

            string projectName = document.ProjectInformation?.Name ?? document.Title ?? "revit_project";
            string dxfPath = LayoutDxfFileExporter.ExportToDocuments(response.IoBundle.Autocad, projectName);
            VastuSession.SetLastExportedDxfPath(dxfPath);

            string constraintLine = constraints.Count > 0
                ? $"\nApplied {constraints.Count} user constraint(s)."
                : string.Empty;

            TaskDialog.Show(
                "Vastu Layout Generated",
                $"New 2D layout ready.\n\n" +
                $"Score: {response.Layout.Metadata.OriginalComplianceScore:0.0}% → " +
                $"{response.Layout.Metadata.GeneratedComplianceScore:0.0}%\n" +
                $"Strategy: {response.Layout.Metadata.GenerationStrategy}" +
                constraintLine +
                $"\n\nDXF exported to:\n{dxfPath}\n\n" +
                "Use 'Generated Layout' on the ribbon to draw it in the active view.");
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Failed to generate Vastu layout: " + ex.Message;
            return Result.Failed;
        }
    }
}
