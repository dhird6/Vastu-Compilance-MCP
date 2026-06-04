using System.Collections.Generic;
using Autodesk.Revit.DB;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public static class VastuSession
{
    private static ComplianceReport? _lastReport;
    private static readonly List<ElementId> _ghostElementIds = new();
    private static string _lastHtmlPath = string.Empty;
    private static string _lastJsonPath = string.Empty;

    public static void SetLastReport(ComplianceReport report)
    {
        _lastReport = report;
    }

    public static ComplianceReport? GetLastReport()
    {
        return _lastReport;
    }

    public static void SetGhostElementIds(IEnumerable<ElementId> ids)
    {
        _ghostElementIds.Clear();
        _ghostElementIds.AddRange(ids);
    }

    public static IReadOnlyList<ElementId> GetGhostElementIds() => _ghostElementIds;

    public static void ClearGhostElements()
    {
        _ghostElementIds.Clear();
    }

    public static void SetLastExportPaths(string htmlPath, string jsonPath)
    {
        _lastHtmlPath = htmlPath;
        _lastJsonPath = jsonPath;
    }

    public static string GetLastHtmlPath() => _lastHtmlPath;

    public static void Clear()
    {
        _lastReport = null;
        _ghostElementIds.Clear();
        _lastHtmlPath = string.Empty;
        _lastJsonPath = string.Empty;
    }
}
