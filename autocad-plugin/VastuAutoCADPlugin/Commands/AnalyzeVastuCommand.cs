using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;
using VastuAutoCADPlugin.Services.Abstractions;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.AnalyzeVastuCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Extracts the active layout, runs Vastu compliance analysis, and exports the HTML report.
    /// </summary>
    public class AnalyzeVastuCommand : DocumentCommandBase
    {
        private readonly IVastuApiClient _apiClient;
        private readonly AutocadLayoutExtractor _extractor;
        private readonly ComplianceReportExporter _exporter;

        public AnalyzeVastuCommand()
            : this(new VastuApiClient(), new AutocadLayoutExtractor(), new ComplianceReportExporter())
        {
        }

        internal AnalyzeVastuCommand(
            IVastuApiClient apiClient,
            AutocadLayoutExtractor extractor,
            ComplianceReportExporter exporter)
        {
            _apiClient = apiClient;
            _extractor = extractor;
            _exporter = exporter;
        }

        [CommandMethod("VASTUANALYZE", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            try
            {
                ResultLayoutRenderer.Clear(document);

                AnalyzeAutocadRequest request = _extractor.BuildAnalyzeRequest(document);
                if (request.Payload.Entities.Count == 0)
                {
                    WriteMessage(
                        editor,
                        "[Vastu] No mapped entities found. Use layer names containing room/wall/door/window.");
                    return;
                }

                AnalyzeComplianceResponse response = _apiClient.AnalyzeAutocadLayout(request);
                VastuSession.SetLastReport(response.Report);

                ExportResult export = _exporter.Export(
                    response.Report,
                    document.Name ?? request.Payload.LayoutName);
                if (export.Success)
                {
                    VastuSession.SetLastExportPaths(export.HtmlPath, export.JsonPath);
                }

                ComplianceReportPresenter.ShowAnalysisSummary(editor, response, export);
            }
            catch (Exception ex)
            {
                WriteError(editor, "Analysis", ex);
            }
        }
    }
}
