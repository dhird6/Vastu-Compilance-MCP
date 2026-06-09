using System;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using VastuAutoCADPlugin.Configuration;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    /// <summary>
    /// Exports Vastu compliance reports to the user's Documents folder.
    /// </summary>
    public sealed class ComplianceReportExporter
    {
        public ExportResult Export(ComplianceReport report, string projectName = null)
        {
            if (report == null)
            {
                return ExportResult.Fail("No report to export.");
            }

            string folder = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                VastuPluginSettings.ReportsFolderName);
            Directory.CreateDirectory(folder);

            string safeProject = SanitizeFileName(projectName ?? "AutoCAD_Layout");
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string baseName = "VastuReport_" + safeProject + "_" + stamp;

            string htmlPath = Path.Combine(folder, baseName + ".html");
            string jsonPath = Path.Combine(folder, baseName + ".json");

            string html = report.HtmlReport;
            if (string.IsNullOrWhiteSpace(html))
            {
                html = "<html><body><p>No HTML report in response. Re-run VASTUANALYZE with MCP server v3+.</p></body></html>";
            }

            File.WriteAllText(htmlPath, html, Encoding.UTF8);
            File.WriteAllText(jsonPath, JsonConvert.SerializeObject(report, Formatting.Indented), Encoding.UTF8);

            return ExportResult.Ok(htmlPath, jsonPath, folder);
        }

        private static string SanitizeFileName(string name)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars())
            {
                name = name.Replace(invalid, '_');
            }

            return name.Length > 40 ? name.Substring(0, 40) : name;
        }
    }

    public sealed class ExportResult
    {
        public bool Success { get; private set; }

        public string HtmlPath { get; private set; }

        public string JsonPath { get; private set; }

        public string Folder { get; private set; }

        public string Message { get; private set; }

        public static ExportResult Ok(string htmlPath, string jsonPath, string folder)
        {
            return new ExportResult
            {
                Success = true,
                HtmlPath = htmlPath,
                JsonPath = jsonPath,
                Folder = folder,
                Message = "Report saved to " + folder,
            };
        }

        public static ExportResult Fail(string message)
        {
            return new ExportResult { Success = false, Message = message };
        }
    }
}
