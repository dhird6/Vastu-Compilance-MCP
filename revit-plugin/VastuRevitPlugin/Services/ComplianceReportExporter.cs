using System;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public class ComplianceReportExporter
{
    public ExportResult Export(ComplianceReport report, string? projectName = null)
    {
        if (report == null)
        {
            return ExportResult.Fail("No report to export.");
        }

        string folder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "VastuReports");
        Directory.CreateDirectory(folder);

        string safeProject = Sanitize(projectName ?? "Project");
        string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        string baseName = $"VastuReport_{safeProject}_{stamp}";

        string htmlPath = Path.Combine(folder, baseName + ".html");
        string jsonPath = Path.Combine(folder, baseName + ".json");

        string html = report.HtmlReport;
        if (string.IsNullOrWhiteSpace(html))
        {
            html = "<html><body><p>No HTML report in response. Re-run Analyze Vastu with MCP server v3+.</p></body></html>";
        }

        File.WriteAllText(htmlPath, html, Encoding.UTF8);
        File.WriteAllText(jsonPath, JsonConvert.SerializeObject(report, Formatting.Indented), Encoding.UTF8);

        return ExportResult.Ok(htmlPath, jsonPath, folder);
    }

    private static string Sanitize(string name)
    {
        foreach (char c in Path.GetInvalidFileNameChars())
        {
            name = name.Replace(c, '_');
        }
        return name.Length > 40 ? name.Substring(0, 40) : name;
    }
}

public class ExportResult
{
    public bool Success { get; init; }
    public string HtmlPath { get; init; } = string.Empty;
    public string JsonPath { get; init; } = string.Empty;
    public string Folder { get; init; } = string.Empty;
    public string Message { get; init; } = string.Empty;

    public static ExportResult Ok(string htmlPath, string jsonPath, string folder) =>
        new ExportResult
        {
            Success = true,
            HtmlPath = htmlPath,
            JsonPath = jsonPath,
            Folder = folder,
            Message = $"Report saved to {folder}",
        };

    public static ExportResult Fail(string message) =>
        new ExportResult { Success = false, Message = message };
}
