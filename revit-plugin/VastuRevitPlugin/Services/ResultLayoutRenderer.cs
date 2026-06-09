using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Solid "Result Layout" overlay from server corrected_payload (same plan, suggestions applied).
/// </summary>
public class ResultLayoutRenderer
{
    private static readonly Color ChangedRoomColor = new Color(40, 200, 120);
    private static readonly Color UnchangedRoomColor = new Color(120, 200, 160);
    private static readonly Color LabelColor = new Color(40, 200, 120);

    public ResultRenderResult Show(Document document, View? view, CorrectedLayoutResult correctedLayout)
    {
        Clear(document);

        if (view == null)
        {
            return ResultRenderResult.Fail("Open a floor plan view to show the result layout.");
        }

        if (correctedLayout?.CorrectedPayload?.Elements == null
            || correctedLayout.CorrectedPayload.Elements.Count == 0)
        {
            return ResultRenderResult.Fail("No corrected layout data in the last report.");
        }

        var changedIds = correctedLayout.ChangesApplied
            .Select(change => change.RoomId)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        var createdIds = new List<ElementId>();
        int roomsDrawn = 0;
        int changedDrawn = 0;

        using Transaction transaction = new Transaction(document, "Vastu Result Layout");
        transaction.Start();

        ElementId? textTypeId = GetDefaultTextNoteType(document);

        foreach (FloorPlanElementDto element in correctedLayout.CorrectedPayload.Elements)
        {
            if (!string.Equals(element.ElementType, "room", StringComparison.OrdinalIgnoreCase)
                || element.Polygon.Count < 3)
            {
                continue;
            }

            bool changed = changedIds.Contains(element.Id)
                || IsMetadataCorrected(element.Metadata);
            Color color = changed ? ChangedRoomColor : UnchangedRoomColor;
            double elevation = ResolveElevation(document, element.Id, view);

            int segments = DrawRoomPolygon(document, view, element.Polygon, elevation, color, changed, createdIds);
            if (segments > 0)
            {
                roomsDrawn++;
                if (changed)
                {
                    changedDrawn++;
                    DrawRoomLabel(document, view, element, elevation, textTypeId, createdIds);
                }
            }
        }

        transaction.Commit();
        VastuSession.SetResultElementIds(createdIds);

        if (roomsDrawn == 0)
        {
            return ResultRenderResult.Fail("Could not draw result layout. Ensure room polygons are valid.");
        }

        return ResultRenderResult.Ok(
            $"Result layout: {roomsDrawn} room(s) ({changedDrawn} with Vastu corrections applied). " +
            $"Score {correctedLayout.OriginalComplianceScore:0.0}% → {correctedLayout.CorrectedComplianceScore:0.0}%.");
    }

    public static void Clear(Document document)
    {
        PreviewGraphicsHelper.ClearResult(document);
    }

    private static bool IsMetadataCorrected(Dictionary<string, object> metadata)
    {
        if (metadata == null || !metadata.TryGetValue("vastu_corrected", out object? value))
        {
            return false;
        }

        return value is bool flag && flag;
    }

    private static double ResolveElevation(Document document, string roomUniqueId, View view)
    {
        Element? element = FindByUniqueId(document, roomUniqueId);
        if (element is Room room)
        {
            Level? level = document.GetElement(room.LevelId) as Level;
            if (level != null)
            {
                return level.Elevation;
            }
        }

        if (view is ViewPlan plan && plan.GenLevel != null)
        {
            return plan.GenLevel.Elevation;
        }

        return 0.0;
    }

    private static int DrawRoomPolygon(
        Document document,
        View view,
        List<Point2DDto> polygon,
        double elevation,
        Color color,
        bool changed,
        List<ElementId> createdIds)
    {
        int count = 0;
        for (int index = 0; index < polygon.Count; index++)
        {
            Point2DDto startPt = polygon[index];
            Point2DDto endPt = polygon[(index + 1) % polygon.Count];
            XYZ start = new XYZ(startPt.X, startPt.Y, elevation);
            XYZ end = new XYZ(endPt.X, endPt.Y, elevation);

            if (start.DistanceTo(end) < 0.05)
            {
                continue;
            }

            Line line = Line.CreateBound(start, end);
            ElementId? curveId = CreateResultCurve(document, view, line, color, changed);
            if (curveId != null)
            {
                createdIds.Add(curveId);
                count++;
            }
        }

        return count;
    }

    private static void DrawRoomLabel(
        Document document,
        View view,
        FloorPlanElementDto element,
        double elevation,
        ElementId? textTypeId,
        List<ElementId> createdIds)
    {
        if (textTypeId == null || element.Polygon.Count == 0)
        {
            return;
        }

        double cx = element.Polygon.Average(point => point.X);
        double cy = element.Polygon.Average(point => point.Y);
        string zone = element.Metadata != null && element.Metadata.TryGetValue("corrected_zone", out object? zoneValue)
            ? zoneValue?.ToString()?.Replace('_', ' ') ?? "corrected"
            : "corrected";

        string label = $"{element.Name}\n✓ {zone}";
        CreateTextNote(
            document,
            view,
            new XYZ(cx, cy, elevation),
            label,
            textTypeId,
            createdIds,
            LabelColor);
    }

    private static void CreateTextNote(
        Document document,
        View view,
        XYZ position,
        string text,
        ElementId? textTypeId,
        List<ElementId> createdIds,
        Color lineColor)
    {
        if (textTypeId == null
            || (view.ViewType != ViewType.FloorPlan && view.ViewType != ViewType.CeilingPlan))
        {
            return;
        }

        try
        {
            TextNoteOptions options = new TextNoteOptions(textTypeId)
            {
                HorizontalAlignment = HorizontalTextAlignment.Center,
            };
            TextNote? note = TextNote.Create(document, view.Id, position, text, options);
            if (note != null)
            {
                OverrideGraphicSettings ogs = new OverrideGraphicSettings();
                ogs.SetProjectionLineColor(lineColor);
                view.SetElementOverrides(note.Id, ogs);
                createdIds.Add(note.Id);
            }
        }
        catch
        {
            // Text notes optional if type unavailable
        }
    }

    private static ElementId? GetDefaultTextNoteType(Document document)
    {
        try
        {
            ElementId id = document.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType);
            return id != ElementId.InvalidElementId ? id : null;
        }
        catch
        {
            return null;
        }
    }

    private static ElementId? CreateResultCurve(
        Document document,
        View view,
        Line line,
        Color color,
        bool changed)
    {
        ElementId? id;
        if (view.ViewType == ViewType.FloorPlan || view.ViewType == ViewType.CeilingPlan)
        {
            DetailCurve? detail = document.Create.NewDetailCurve(view, line);
            id = detail?.Id;
        }
        else
        {
            Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, line.GetEndPoint(0));
            SketchPlane sketchPlane = SketchPlane.Create(document, plane);
            ModelCurve modelCurve = document.Create.NewModelCurve(line, sketchPlane);
            id = modelCurve.Id;
        }

        if (id != null)
        {
            ApplyResultStyle(view, id, color, changed ? 9 : 5);
        }

        return id;
    }

    private static void ApplyResultStyle(View view, ElementId elementId, Color color, int weight)
    {
        OverrideGraphicSettings ogs = new OverrideGraphicSettings();
        ogs.SetProjectionLineColor(color);
        ogs.SetProjectionLineWeight(weight);
        view.SetElementOverrides(elementId, ogs);
    }

    private static Element? FindByUniqueId(Document document, string uniqueId)
    {
        return new FilteredElementCollector(document)
            .WhereElementIsNotElementType()
            .FirstOrDefault(element => element.UniqueId == uniqueId);
    }
}

public class ResultRenderResult
{
    public bool Success { get; init; }
    public string Message { get; init; } = string.Empty;

    public static ResultRenderResult Ok(string message) =>
        new ResultRenderResult { Success = true, Message = message };

    public static ResultRenderResult Fail(string message) =>
        new ResultRenderResult { Success = false, Message = message };
}
