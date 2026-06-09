using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ExportReportCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Re-exports or opens the last Vastu HTML report with company branding and comparison visuals.
    /// </summary>
    public class ExportReportCommand : DocumentCommandBase
    {
        private readonly ComplianceReportExporter _exporter;

        public ExportReportCommand()
            : this(new ComplianceReportExporter())
        {
        }

        internal ExportReportCommand(ComplianceReportExporter exporter)
        {
            _exporter = exporter;
        }

        [CommandMethod("VASTUEXPORTREPORT", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            ComplianceReport report = VastuSession.GetLastReport();
            if (report == null)
            {
                WriteMessage(editor, "[Vastu] No report available. Run VASTUANALYZE first.");
                return;
            }

            try
            {
                ExportResult export = _exporter.Export(report, document.Name ?? "AutoCAD_Layout");
                if (!export.Success)
                {
                    WriteMessage(editor, "[Vastu] " + export.Message);
                    return;
                }

                VastuSession.SetLastExportPaths(export.HtmlPath, export.JsonPath);
                WriteMessage(editor, "[Vastu] Report exported: " + export.HtmlPath);
                WriteMessage(editor, "[Vastu] JSON data: " + export.JsonPath);
                ComplianceReportPresenter.OpenHtmlReport(export);
            }
            catch (Exception ex)
            {
                WriteError(editor, "Report export", ex);
            }
        }
    }
}
