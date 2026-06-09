using System;
using System.IO;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public static class LayoutDxfFileExporter
{
    public static string ExportToDocuments(AutocadLayoutExportDto export, string projectName)
    {
        if (export == null)
        {
            throw new ArgumentNullException(nameof(export));
        }

        string folder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "VastuLayouts");
        Directory.CreateDirectory(folder);

        string baseName = SanitizeFileName(projectName);
        if (string.IsNullOrWhiteSpace(baseName))
        {
            baseName = "vastu_layout";
        }

        string fileName = !string.IsNullOrWhiteSpace(export.FilenameHint)
            ? SanitizeFileName(Path.GetFileNameWithoutExtension(export.FilenameHint)) + ".dxf"
            : baseName + "_vastu_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".dxf";

        string path = Path.Combine(folder, fileName);

        if (!string.IsNullOrWhiteSpace(export.DxfBase64))
        {
            File.WriteAllBytes(path, Convert.FromBase64String(export.DxfBase64));
            return path;
        }

        throw new InvalidOperationException(
            "No DXF bytes returned. Install ezdxf on the MCP server or re-run layout generation.");
    }

    private static string SanitizeFileName(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }

        foreach (char invalid in Path.GetInvalidFileNameChars())
        {
            value = value.Replace(invalid, '_');
        }

        return value.Trim();
    }
}
