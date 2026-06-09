using System;
using System.Diagnostics;
using System.Linq;
using System.Text;
using Autodesk.AutoCAD.EditorInput;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    /// <summary>
    /// Presents compliance results in the AutoCAD command line and opens exported reports.
    /// </summary>
    public static class ComplianceReportPresenter
    {
        public static void ShowAnalysisSummary(Editor editor, AnalyzeComplianceResponse response, ExportResult export)
        {
            VastuAnalysisSummaryBuilder.WriteSummary(editor, response);

            if (export != null && export.Success)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] Report exported: " + export.HtmlPath);
                editor.WriteMessage(Environment.NewLine + "[Vastu] Run VASTUEXPORTREPORT to re-export or open the HTML report.");
            }
        }

        public static void OpenHtmlReport(ExportResult export)
        {
            if (export == null || !export.Success || string.IsNullOrWhiteSpace(export.HtmlPath))
            {
                return;
            }

            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = export.HtmlPath,
                    UseShellExecute = true,
                });
            }
            catch
            {
                // Ignore browser launch failures.
            }
        }

        public static void OpenReportsFolder(ExportResult export)
        {
            if (export == null || !export.Success || string.IsNullOrWhiteSpace(export.Folder))
            {
                return;
            }

            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = export.Folder,
                    UseShellExecute = true,
                });
            }
            catch
            {
                // Ignore folder launch failures.
            }
        }
    }

    /// <summary>
    /// Builds readable command-line summaries from compliance reports.
    /// </summary>
    public static class VastuAnalysisSummaryBuilder
    {
        public static void WriteSummary(Editor editor, AnalyzeComplianceResponse response)
        {
            if (response?.Report?.Summary == null)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] Server returned empty report.");
                return;
            }

            ComplianceSummary summary = response.Report.Summary;
            editor.WriteMessage(Environment.NewLine + "[Vastu] Compliance Score: " + summary.ComplianceScore.ToString("0.00"));
            editor.WriteMessage(Environment.NewLine + "[Vastu] Grade: " + summary.Grade);
            editor.WriteMessage(Environment.NewLine + "[Vastu] Passed: " + summary.PassedRules + ", Failed: " + summary.FailedRules);

            if (response.Report.RemediationPlan != null
                && !string.IsNullOrWhiteSpace(response.Report.RemediationPlan.Summary))
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] " + response.Report.RemediationPlan.Summary);
            }

            if (response.Report.CorrectedLayout != null
                && response.Report.CorrectedLayout.ChangesApplied != null
                && response.Report.CorrectedLayout.ChangesApplied.Count > 0)
            {
                editor.WriteMessage(
                    Environment.NewLine +
                    "[Vastu] Result layout ready: " +
                    response.Report.CorrectedLayout.OriginalComplianceScore.ToString("0.0") + "% -> " +
                    response.Report.CorrectedLayout.CorrectedComplianceScore.ToString("0.0") + "%");
                editor.WriteMessage(Environment.NewLine + "[Vastu] Run VASTURESULT to draw corrected 2D layout.");
            }

            var top = response.Report.Recommendations.Take(3).ToList();
            if (top.Count == 0)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] No recommendations. Layout appears compliant.");
                return;
            }

            editor.WriteMessage(Environment.NewLine + "[Vastu] Top recommendations:");
            for (int index = 0; index < top.Count; index++)
            {
                string reference = top[index].ScripturalReferences != null && top[index].ScripturalReferences.Any()
                    ? " | Ref: " + top[index].ScripturalReferences.First()
                    : string.Empty;
                editor.WriteMessage(Environment.NewLine + "  " + (index + 1) + ". " + top[index].Text + reference);
            }
        }
    }
}
