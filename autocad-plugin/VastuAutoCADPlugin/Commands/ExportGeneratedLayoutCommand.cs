using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ExportGeneratedLayoutCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Exports the last generated layout to DXF in the user's Documents folder.
    /// </summary>
    public class ExportGeneratedLayoutCommand : DocumentCommandBase
    {
        [CommandMethod("VASTUEXPORTGENERATED", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            GenerateLayoutFromReportResponse generated = VastuSession.GetLastGeneratedLayout();
            if (generated?.IoBundle?.Autocad == null)
            {
                WriteMessage(editor, "[Vastu] No generated layout available. Run VASTUGENERATE first.");
                return;
            }

            try
            {
                string path = LayoutDxfFileExporter.ExportToDocuments(
                    generated.IoBundle.Autocad,
                    document.Name ?? "autocad_layout");
                VastuSession.SetLastExportedDxfPath(path);
                WriteMessage(editor, "[Vastu] DXF exported: " + path);
            }
            catch (Exception ex)
            {
                WriteError(editor, "DXF export", ex);
            }
        }
    }
}
