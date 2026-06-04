using System;
using System.Linq;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services;

namespace VastuAutoCADPlugin.Commands
{
    public class VastuCommands
    {
        [CommandMethod("VASTUANALYZE")]
        public void AnalyzeLayout()
        {
            Document document = Application.DocumentManager.MdiActiveDocument;
            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;
            try
            {
                var extractor = new AutocadLayoutExtractor();
                AnalyzeAutocadRequest request = extractor.BuildAnalyzeRequest(document);

                if (request.Payload.Entities.Count == 0)
                {
                    editor.WriteMessage(
                        Environment.NewLine +
                        "[Vastu] No mapped entities found. Use layer names containing room/wall/door/window."
                    );
                    return;
                }

                var apiClient = new VastuApiClient();
                AnalyzeComplianceResponse response = apiClient.AnalyzeAutocadLayout(request);
                PrintSummary(editor, response);
            }
            catch (System.Exception ex)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] Analysis failed: " + ex.Message);
            }
        }

        private static void PrintSummary(Editor editor, AnalyzeComplianceResponse response)
        {
            if (response?.Report?.Summary == null)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] Server returned empty report.");
                return;
            }

            var summary = response.Report.Summary;
            editor.WriteMessage(Environment.NewLine + "[Vastu] Compliance Score: " + summary.ComplianceScore.ToString("0.00"));
            editor.WriteMessage(Environment.NewLine + "[Vastu] Grade: " + summary.Grade);
            editor.WriteMessage(Environment.NewLine + "[Vastu] Passed: " + summary.PassedRules + ", Failed: " + summary.FailedRules);

            var top = response.Report.Recommendations.Take(3).ToList();
            if (top.Count == 0)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] No recommendations. Layout appears compliant.");
                return;
            }

            editor.WriteMessage(Environment.NewLine + "[Vastu] Top recommendations:");
            for (int i = 0; i < top.Count; i++)
            {
                string reference = top[i].ScripturalReferences.Any()
                    ? " | Ref: " + top[i].ScripturalReferences.First()
                    : string.Empty;
                editor.WriteMessage(Environment.NewLine + "  " + (i + 1) + ". " + top[i].Text + reference);
            }
        }
    }
}
