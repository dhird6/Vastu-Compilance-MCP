using System.Collections.Generic;
using Autodesk.Revit.DB;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public static class VastuSession
{
    private static ComplianceReport? _lastReport;
    private static GenerateLayoutFromReportResponse? _lastGeneratedLayout;
    private static string _lastExportedDxfPath = string.Empty;
    private static readonly List<UserLayoutConstraintDto> _layoutConstraints = new();
    private static readonly List<ElementId> _ghostElementIds = new();
    private static readonly List<ElementId> _resultElementIds = new();
    private static readonly List<ElementId> _generatedElementIds = new();
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

    public static void SetLastGeneratedLayout(GenerateLayoutFromReportResponse layout)
    {
        _lastGeneratedLayout = layout;
    }

    public static GenerateLayoutFromReportResponse? GetLastGeneratedLayout()
    {
        return _lastGeneratedLayout;
    }

    public static void SetLastExportedDxfPath(string path)
    {
        _lastExportedDxfPath = path;
    }

    public static string GetLastExportedDxfPath() => _lastExportedDxfPath;

    public static IReadOnlyList<UserLayoutConstraintDto> GetLayoutConstraints() => _layoutConstraints;

    public static void AddLayoutConstraint(UserLayoutConstraintDto constraint)
    {
        if (string.IsNullOrWhiteSpace(constraint.ConstraintId))
        {
            return;
        }

        _layoutConstraints.RemoveAll(item => item.ConstraintId == constraint.ConstraintId);
        _layoutConstraints.Add(constraint);
    }

    public static void ClearLayoutConstraints()
    {
        _layoutConstraints.Clear();
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

    public static void SetResultElementIds(IEnumerable<ElementId> ids)
    {
        _resultElementIds.Clear();
        _resultElementIds.AddRange(ids);
    }

    public static IReadOnlyList<ElementId> GetResultElementIds() => _resultElementIds;

    public static void ClearResultElements()
    {
        _resultElementIds.Clear();
    }

    public static void SetGeneratedElementIds(IEnumerable<ElementId> ids)
    {
        _generatedElementIds.Clear();
        _generatedElementIds.AddRange(ids);
    }

    public static IReadOnlyList<ElementId> GetGeneratedElementIds() => _generatedElementIds;

    public static void ClearGeneratedElements()
    {
        _generatedElementIds.Clear();
    }

    public static void ClearAllPreviewGraphics()
    {
        _ghostElementIds.Clear();
        _resultElementIds.Clear();
        _generatedElementIds.Clear();
    }

    public static int GetPreviewElementCount() =>
        _ghostElementIds.Count + _resultElementIds.Count + _generatedElementIds.Count;

    public static void SetLastExportPaths(string htmlPath, string jsonPath)
    {
        _lastHtmlPath = htmlPath;
        _lastJsonPath = jsonPath;
    }

    public static string GetLastHtmlPath() => _lastHtmlPath;

    public static void Clear()
    {
        _lastReport = null;
        ClearAllPreviewGraphics();
        _lastHtmlPath = string.Empty;
        _lastJsonPath = string.Empty;
    }
}
