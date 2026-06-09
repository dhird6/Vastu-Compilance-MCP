using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ClearResultLayoutCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Removes corrected layout graphics from the active drawing.
    /// </summary>
    public class ClearResultLayoutCommand : DocumentCommandBase
    {
        [CommandMethod("VASTUCLEARRESULT", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            int count = VastuSession.GetResultEntityHandles().Count;
            if (count == 0)
            {
                WriteMessage(editor, "[Vastu] No result layout graphics are active.");
                return;
            }

            ResultLayoutRenderer.Clear(document);
            WriteMessage(editor, "[Vastu] Removed result layout (" + count + " entity/entities).");
        }
    }
}
