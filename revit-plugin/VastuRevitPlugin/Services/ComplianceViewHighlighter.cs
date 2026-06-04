using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Autodesk.Revit.DB;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Applies heatmap color overrides to rooms in the active view from MCP report.
/// </summary>
public class ComplianceViewHighlighter
{
    public int ApplyHeatmap(Document document, View? view, ComplianceReport report)
    {
        if (view == null || report.Heatmap == null || report.Heatmap.Count == 0)
        {
            return 0;
        }

        var heatByRoom = new Dictionary<string, HeatmapCell>(StringComparer.Ordinal);
        foreach (HeatmapCell cell in report.Heatmap)
        {
            heatByRoom[cell.RoomId] = cell;
        }

        int applied = 0;
        using Transaction transaction = new Transaction(document, "Vastu Heatmap Highlights");
        transaction.Start();

        foreach (KeyValuePair<string, HeatmapCell> entry in heatByRoom)
        {
            Element? element = FindByUniqueId(document, entry.Key);
            if (element == null)
            {
                continue;
            }

            Color? color = ParseHexColor(entry.Value.ColorHex);
            if (color == null)
            {
                continue;
            }

            OverrideGraphicSettings ogs = new OverrideGraphicSettings();
            ogs.SetSurfaceForegroundPatternColor(color);
            ogs.SetSurfaceForegroundPatternVisible(true);
            ogs.SetProjectionLineColor(color);
            ogs.SetProjectionLineWeight(4);
            view.SetElementOverrides(element.Id, ogs);
            applied++;
        }

        transaction.Commit();
        return applied;
    }

    public static void ClearHeatmap(Document document, View? view, ComplianceReport? report)
    {
        if (view == null || report?.Heatmap == null)
        {
            return;
        }

        using Transaction transaction = new Transaction(document, "Clear Vastu Heatmap");
        transaction.Start();
        foreach (HeatmapCell cell in report.Heatmap)
        {
            Element? element = FindByUniqueId(document, cell.RoomId);
            if (element != null)
            {
                view.SetElementOverrides(element.Id, new OverrideGraphicSettings());
            }
        }
        transaction.Commit();
    }

    private static Color? ParseHexColor(string hex)
    {
        if (string.IsNullOrWhiteSpace(hex) || !hex.StartsWith("#", StringComparison.Ordinal))
        {
            return null;
        }

        string value = hex.TrimStart('#');
        if (value.Length != 6)
        {
            return null;
        }

        try
        {
            int r = int.Parse(value.Substring(0, 2), NumberStyles.HexNumber);
            int g = int.Parse(value.Substring(2, 2), NumberStyles.HexNumber);
            int b = int.Parse(value.Substring(4, 2), NumberStyles.HexNumber);
            return new Color((byte)r, (byte)g, (byte)b);
        }
        catch
        {
            return null;
        }
    }

    private static Element? FindByUniqueId(Document document, string uniqueId)
    {
        return new FilteredElementCollector(document)
            .WhereElementIsNotElementType()
            .FirstOrDefault(element => element.UniqueId == uniqueId);
    }
}
