using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ClearGeneratedLayoutCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Removes generated layout graphics from the active drawing.
    /// </summary>
    public class ClearGeneratedLayoutCommand : DocumentCommandBase
    {
        [CommandMethod("VASTUCLEARGENERATED", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            int count = VastuSession.GetGeneratedEntityHandles().Count;
            if (count == 0)
            {
                WriteMessage(editor, "[Vastu] No generated layout graphics are active.");
                return;
            }

            GeneratedLayoutRenderer.Clear(document);
            WriteMessage(editor, "[Vastu] Removed generated layout (" + count + " entity/entities).");
        }
    }
}
