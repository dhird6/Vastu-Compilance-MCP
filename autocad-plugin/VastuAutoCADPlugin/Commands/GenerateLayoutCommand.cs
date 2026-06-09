using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;
using VastuAutoCADPlugin.Services.Abstractions;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.GenerateLayoutCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Generates a new Vastu-compliant layout from the last compliance report.
    /// </summary>
    public class GenerateLayoutCommand : DocumentCommandBase
    {
        private readonly IVastuApiClient _apiClient;
        private readonly AutocadLayoutExtractor _extractor;

        public GenerateLayoutCommand()
            : this(new VastuApiClient(), new AutocadLayoutExtractor())
        {
        }

        internal GenerateLayoutCommand(IVastuApiClient apiClient, AutocadLayoutExtractor extractor)
        {
            _apiClient = apiClient;
            _extractor = extractor;
        }

        [CommandMethod("VASTUGENERATE", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            try
            {
                GeneratedLayoutRenderer.Clear(document);

                FloorPlanPayloadDto payload = _extractor.BuildFloorPlanPayload(document);
                if (payload.Elements.Count == 0)
                {
                    WriteMessage(editor, "[Vastu] No room polygons found. Use layers containing 'room'.");
                    return;
                }

                ComplianceReport report = VastuSession.GetLastReport();
                IReadOnlyList<UserLayoutConstraintDto> constraints = VastuSession.GetLayoutConstraints();
                var request = new GenerateLayoutFromReportRequest
                {
                    Payload = payload,
                    Report = report,
                    UserConstraints = new List<UserLayoutConstraintDto>(constraints),
                    UseLlmPlanner = true,
                    GenerateSvgPreview = true,
                };

                GenerateLayoutFromReportResponse response = _apiClient.GenerateLayoutFromReport(request);
                VastuSession.SetLastGeneratedLayout(response);

                string dxfPath = LayoutDxfFileExporter.ExportToDocuments(
                    response.IoBundle.Autocad,
                    document.Name ?? "autocad_layout");
                VastuSession.SetLastExportedDxfPath(dxfPath);

                WriteMessage(editor, "[Vastu] New layout generated.");
                if (constraints.Count > 0)
                {
                    WriteMessage(
                        editor,
                        Environment.NewLine + "[Vastu] Applied " + constraints.Count + " user constraint(s).");
                }

                WriteMessage(
                    editor,
                    Environment.NewLine +
                    "[Vastu] Score: " +
                    response.Layout.Metadata.OriginalComplianceScore.ToString("0.0") + "% -> " +
                    response.Layout.Metadata.GeneratedComplianceScore.ToString("0.0") + "% " +
                    "(" + response.Layout.Metadata.GenerationStrategy + ")");
                WriteMessage(editor, Environment.NewLine + "[Vastu] DXF exported: " + dxfPath);
                WriteMessage(editor, Environment.NewLine + "[Vastu] Run VASTUSHOWGENERATED to draw the new layout.");
            }
            catch (Exception ex)
            {
                WriteError(editor, "Layout generation", ex);
            }
        }
    }
}
