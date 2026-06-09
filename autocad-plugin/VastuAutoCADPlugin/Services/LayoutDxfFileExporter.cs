using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public static class LayoutDxfFileExporter
    {
        public static string ExportToDocuments(AutocadLayoutExport export, string projectName)
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

            if (export.DxfBlueprint?.Entities != null && export.DxfBlueprint.Entities.Count > 0)
            {
                WriteBlueprintDxf(path, export.DxfBlueprint);
                return path;
            }

            throw new InvalidOperationException("No DXF data available in the generated layout response.");
        }

        private static void WriteBlueprintDxf(string path, DxfBlueprint blueprint)
        {
            var builder = new StringBuilder();
            builder.AppendLine("  0");
            builder.AppendLine("SECTION");
            builder.AppendLine("  2");
            builder.AppendLine("ENTITIES");

            foreach (DxfEntity entity in blueprint.Entities)
            {
                if (string.Equals(entity.Type, "LWPOLYLINE", StringComparison.OrdinalIgnoreCase)
                    && entity.Points != null
                    && entity.Points.Count >= 3)
                {
                    builder.AppendLine("  0");
                    builder.AppendLine("LWPOLYLINE");
                    builder.AppendLine("  8");
                    builder.AppendLine(entity.Layer ?? "VASTU_ROOMS");
                    builder.AppendLine(" 90");
                    builder.AppendLine(entity.Points.Count.ToString());
                    builder.AppendLine(" 70");
                    builder.AppendLine(entity.Closed ? "1" : "0");
                    foreach (Point2D point in entity.Points)
                    {
                        builder.AppendLine(" 10");
                        builder.AppendLine(point.X.ToString("0.###"));
                        builder.AppendLine(" 20");
                        builder.AppendLine(point.Y.ToString("0.###"));
                    }
                }
                else if (string.Equals(entity.Type, "LINE", StringComparison.OrdinalIgnoreCase)
                    && entity.Start != null
                    && entity.End != null)
                {
                    builder.AppendLine("  0");
                    builder.AppendLine("LINE");
                    builder.AppendLine("  8");
                    builder.AppendLine(entity.Layer ?? "VASTU_WALLS");
                    builder.AppendLine(" 10");
                    builder.AppendLine(entity.Start.X.ToString("0.###"));
                    builder.AppendLine(" 20");
                    builder.AppendLine(entity.Start.Y.ToString("0.###"));
                    builder.AppendLine(" 11");
                    builder.AppendLine(entity.End.X.ToString("0.###"));
                    builder.AppendLine(" 21");
                    builder.AppendLine(entity.End.Y.ToString("0.###"));
                }
            }

            builder.AppendLine("  0");
            builder.AppendLine("ENDSEC");
            builder.AppendLine("  0");
            builder.AppendLine("EOF");
            File.WriteAllText(path, builder.ToString(), Encoding.ASCII);
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
}
