using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public class RemediationExecutor
{
    private readonly RoomGeometryAligner _geometryAligner = new RoomGeometryAligner();

    public RemediationApplyResult Apply(
        Document document,
        RemediationPlan plan,
        RemediationApplyMode mode)
    {
        var result = new RemediationApplyResult();
        View? view = document.ActiveView;
        var processedGeometryRooms = new HashSet<string>(StringComparer.Ordinal);

        using Transaction transaction = new Transaction(document, "Apply Vastu Remediation");
        transaction.Start();

        foreach (RemediationAction action in plan.Actions)
        {
            if (!ShouldRun(action, mode))
            {
                result.SkippedCount++;
                continue;
            }

            Element? element = FindByUniqueId(document, action.RoomId);
            if (element == null)
            {
                result.FailedCount++;
                result.Messages.Add($"Element not found: {action.RoomId}");
                continue;
            }

            try
            {
                switch (action.ActionType)
                {
                    case "highlight_room":
                        if (view != null)
                        {
                            ApplyHighlight(view, element.Id);
                            result.AppliedCount++;
                        }
                        break;

                    case "set_parameter":
                        ApplyComments(element, action);
                        result.AppliedCount++;
                        break;

                    case "annotate":
                        ApplyAnnotation(element);
                        result.AppliedCount++;
                        break;

                    case "draw_zone_guide":
                        if (element is Room guideRoom)
                        {
                            GeometryApplyResult guideResult = _geometryAligner.DrawZoneGuide(
                                document, view, guideRoom, action);
                            RecordGeometryResult(guideResult, result);
                        }
                        break;

                    case "move_room_boundaries":
                        if (element is Room boundaryRoom &&
                            processedGeometryRooms.Add(action.RoomId))
                        {
                            GeometryApplyResult moveResult = _geometryAligner.ApplyBoundaryMove(
                                document, boundaryRoom, action);
                            RecordGeometryResult(moveResult, result);
                        }
                        break;

                    case "show_ghost_design":
                        // Preview-only — handled by GhostDesignRenderer, not apply
                        result.SkippedCount++;
                        break;

                    default:
                        result.SkippedCount++;
                        break;
                }
            }
            catch (Exception ex)
            {
                result.FailedCount++;
                result.Messages.Add($"{action.ActionId}: {ex.Message}");
            }
        }

        transaction.Commit();
        return result;
    }

    public static int CountGeometryActions(RemediationPlan plan) =>
        plan.Actions.Count(action => action.ActionType == "move_room_boundaries");

    public static int CountSafeActions(RemediationPlan plan) =>
        plan.Actions.Count(action => action.AutoApplicable);

    private static bool ShouldRun(RemediationAction action, RemediationApplyMode mode)
    {
        return mode switch
        {
            RemediationApplyMode.SafeOnly => action.AutoApplicable,
            RemediationApplyMode.GeometryOnly => action.ActionType == "move_room_boundaries",
            RemediationApplyMode.FullPlan => action.AutoApplicable
                || action.ActionType == "move_room_boundaries",
            _ => false,
        };
    }

    private static void RecordGeometryResult(GeometryApplyResult geometryResult, RemediationApplyResult result)
    {
        if (geometryResult.Success)
        {
            result.AppliedCount++;
            result.Messages.Add(geometryResult.Message);
        }
        else
        {
            result.FailedCount++;
            result.Messages.Add(geometryResult.Message);
        }
    }

    private static Element? FindByUniqueId(Document document, string uniqueId)
    {
        return new FilteredElementCollector(document)
            .WhereElementIsNotElementType()
            .FirstOrDefault(element => element.UniqueId == uniqueId);
    }

    private static void ApplyHighlight(View view, ElementId elementId)
    {
        OverrideGraphicSettings ogs = new OverrideGraphicSettings();
        ogs.SetProjectionLineColor(new Color(255, 102, 0));
        ogs.SetSurfaceForegroundPatternColor(new Color(255, 200, 0));
        ogs.SetSurfaceForegroundPatternVisible(true);
        view.SetElementOverrides(elementId, ogs);
    }

    private static void ApplyComments(Element element, RemediationAction action)
    {
        if (!action.Parameters.TryGetValue("VastuTargetZone", out object? targetObj))
        {
            return;
        }

        string target = targetObj?.ToString() ?? string.Empty;
        string compliant = action.Parameters.TryGetValue("VastuCompliant", out object? c)
            ? c?.ToString() ?? "False"
            : "False";
        string ruleId = action.Parameters.TryGetValue("VastuRuleId", out object? r)
            ? r?.ToString() ?? string.Empty
            : string.Empty;

        Parameter? comments = element.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
        if (comments != null && !comments.IsReadOnly)
        {
            comments.Set($"Vastu: compliant={compliant}; target={target}; rule={ruleId}");
        }
    }

    private static void ApplyAnnotation(Element element)
    {
        if (element is Room room)
        {
            Parameter? nameParam = room.get_Parameter(BuiltInParameter.ROOM_NAME);
            if (nameParam != null && !nameParam.IsReadOnly)
            {
                string current = nameParam.AsString() ?? room.Name;
                if (!current.Contains("[Vastu]", StringComparison.Ordinal))
                {
                    nameParam.Set($"{current} [Vastu]");
                }
            }
        }
    }
}

public enum RemediationApplyMode
{
    SafeOnly,
    GeometryOnly,
    FullPlan,
}

public class RemediationApplyResult
{
    public int AppliedCount { get; set; }
    public int SkippedCount { get; set; }
    public int FailedCount { get; set; }
    public List<string> Messages { get; set; } = new();

    public string Summary =>
        $"Applied: {AppliedCount}, Skipped: {SkippedCount}, Failed: {FailedCount}";
}
