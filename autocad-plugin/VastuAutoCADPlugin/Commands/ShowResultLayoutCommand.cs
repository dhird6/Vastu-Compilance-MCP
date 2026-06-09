using System;
using System.Linq;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Commands.Base;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;

[assembly: CommandClass(typeof(VastuAutoCADPlugin.Commands.ShowResultLayoutCommand))]

namespace VastuAutoCADPlugin.Commands
{
    /// <summary>
    /// Draws the Vastu-corrected 2D layout overlay in the active drawing.
    /// </summary>
    public class ShowResultLayoutCommand : DocumentCommandBase
    {
        [CommandMethod("VASTURESULT", CommandFlags.Modal)]
        public void Execute()
        {
            if (!TryGetActiveDocument(out Document document, out Editor editor))
            {
                return;
            }

            ComplianceReport report = VastuSession.GetLastReport();
            if (report?.CorrectedLayout?.CorrectedPayload?.Elements == null
                || report.CorrectedLayout.CorrectedPayload.Elements.Count == 0)
            {
                WriteMessage(editor, "[Vastu] No corrected layout available. Run VASTUANALYZE first.");
                return;
            }

            try
            {
                ResultRenderResult result = new ResultLayoutRenderer().Show(document, report.CorrectedLayout);
                WriteMessage(editor, "[Vastu] " + result.Message);

                if (report.CorrectedLayout.ChangesApplied != null)
                {
                    foreach (AppliedLayoutChange change in report.CorrectedLayout.ChangesApplied.Take(6))
                    {
                        WriteMessage(
                            editor,
                            Environment.NewLine +
                            "  - " + change.RoomName + ": " + change.OriginalZone + " -> " + change.CorrectedZone);
                    }
                }

                WriteMessage(
                    editor,
                    Environment.NewLine +
                    "[Vastu] Layers: VASTU_RESULT (all rooms), VASTU_RESULT_CHANGED (corrected rooms).");
                WriteMessage(editor, Environment.NewLine + "[Vastu] Run VASTUCLEARRESULT to remove.");
            }
            catch (Exception ex)
            {
                WriteError(editor, "Result layout", ex);
            }
        }
    }
}
