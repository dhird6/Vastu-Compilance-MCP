using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ConfigureConstraintsCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Opens the interactive layout constraint editor for user-preserved rooms.
    /// </summary>
    public class ConfigureConstraintsCommand : DocumentCommandBase
    {
        [CommandMethod("VASTUCONSTRAINTS", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out _))
            {
                return;
            }

            LayoutConstraintEditor.RunInteractiveMenu(document);
        }
    }
}
