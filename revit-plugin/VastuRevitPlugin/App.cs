using System;
using Autodesk.Revit.UI;

namespace VastuRevitPlugin;

public class App : IExternalApplication
{
    private const string TabName = "Vastu Compliance";
    private const string PanelName = "Analysis";

    public Result OnStartup(UIControlledApplication application)
    {
        try
        {
            try
            {
                application.CreateRibbonTab(TabName);
            }
            catch
            {
                // Tab may already exist in the session.
            }

            RibbonPanel panel = application.CreateRibbonPanel(TabName, PanelName);
            string assemblyPath = typeof(App).Assembly.Location;

            AddButton(panel, assemblyPath, "AnalyzeVastu", "Analyze\nVastu",
                typeof(Commands.AnalyzeVastuCommand).FullName!,
                "Full analysis: heatmap, HTML report, structured results.");

            AddButton(panel, assemblyPath, "ExportReport", "Export\nReport",
                typeof(Commands.ExportReportCommand).FullName!,
                "Export HTML + JSON report to Documents/VastuReports.");

            AddButton(panel, assemblyPath, "PreviewVastu", "Ghost\nPreview",
                typeof(Commands.PreviewVastuCommand).FullName!,
                "Show ghost design: proposed room layout from remediation plan.");

            AddButton(panel, assemblyPath, "ClearGhost", "Clear\nGhost",
                typeof(Commands.ClearGhostDesignCommand).FullName!,
                "Remove ghost design preview graphics from the model.");

            AddButton(panel, assemblyPath, "ApplyRemediation", "Apply\nRemediation",
                typeof(Commands.ApplyRemediationCommand).FullName!,
                "Apply full RemediationPlan: safe fixes, guides, and approved wall moves.");

            AddButton(panel, assemblyPath, "ApplyVastu", "Safe Fixes\nOnly",
                typeof(Commands.ApplyVastuCommand).FullName!,
                "Apply only auto-applicable fixes without moving walls.");
        }
        catch (Exception)
        {
            return Result.Failed;
        }

        return Result.Succeeded;
    }

    public Result OnShutdown(UIControlledApplication application)
    {
        return Result.Succeeded;
    }

    private static void AddButton(
        RibbonPanel panel,
        string assemblyPath,
        string id,
        string label,
        string className,
        string tooltip)
    {
        PushButtonData buttonData = new PushButtonData(id, label, assemblyPath, className);
        buttonData.ToolTip = tooltip;
        panel.AddItem(buttonData);
    }
}
