using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;

namespace VastuAutoCADPlugin.Commands.Base
{
    /// <summary>
    /// Shared helpers for AutoCAD commands following Autodesk extension patterns.
    /// </summary>
    public abstract class DocumentCommandBase
    {
        protected static bool TryGetActiveDocument(out Document document, out Editor editor)
        {
            document = Application.DocumentManager.MdiActiveDocument;
            if (document == null)
            {
                editor = null;
                return false;
            }

            editor = document.Editor;
            return true;
        }

        protected static void WriteMessage(Editor editor, string message)
        {
            if (editor == null || string.IsNullOrWhiteSpace(message))
            {
                return;
            }

            editor.WriteMessage(Environment.NewLine + message);
        }

        protected static void WriteError(Editor editor, string operation, Exception exception)
        {
            WriteMessage(editor, "[Vastu] " + operation + " failed: " + exception.Message);
        }
    }
}
