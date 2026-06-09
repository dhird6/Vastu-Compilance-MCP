using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ShowGeneratedLayoutCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Draws the generated Vastu layout in the active drawing.
    /// </summary>
    public class ShowGeneratedLayoutCommand : DocumentCommandBase
    {
        [CommandMethod("VASTUSHOWGENERATED", CommandFlags.Modal)]
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
                ResultRenderResult result = new GeneratedLayoutRenderer().Show(document, generated.IoBundle.Autocad);
                WriteMessage(editor, "[Vastu] " + result.Message);
                WriteMessage(
                    editor,
                    Environment.NewLine +
                    "[Vastu] Layers: VASTU_GENERATED, VASTU_GENERATED_PLOT, VASTU_GENERATED_WALL.");
                WriteMessage(editor, Environment.NewLine + "[Vastu] Run VASTUCLEARGENERATED to remove.");
            }
            catch (Exception ex)
            {
                WriteError(editor, "Show generated layout", ex);
            }
        }
    }
}
