using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Advanced ghost design: proposed outlines, shift arrows, labels, and zone compass.
/// </summary>
public class GhostDesignRenderer
{
    private static readonly Color GhostLineColor = new Color(0, 220, 180);
    private static readonly Color GhostArrowColor = new Color(255, 200, 50);
    private static readonly Color CompassColor = new Color(120, 160, 255);

    public GhostRenderResult Show(Document document, View? view, RemediationPlan plan)
    {
        Clear(document);

        if (view == null)
        {
            return GhostRenderResult.Fail("Open a floor plan view to show ghost design preview.");
        }

        var ghostActions = plan.Actions
            .Where(action =>
                action.ActionType is "show_ghost_design" or "move_room_boundaries")
            .GroupBy(action => action.RoomId)
            .Select(group => group.FirstOrDefault(a => a.ActionType == "show_ghost_design") ?? group.First())
            .ToList();

        if (ghostActions.Count == 0)
        {
            return GhostRenderResult.Fail("No geometry remediation actions to preview.");
        }

        var createdIds = new List<ElementId>();
        var plotCenters = new List<XYZ>();
        int roomsDrawn = 0;

        using Transaction transaction = new Transaction(document, "Vastu Ghost Design Preview");
        transaction.Start();

        ElementId? textTypeId = GetDefaultTextNoteType(document);

        foreach (RemediationAction action in ghostActions)
        {
            Element? element = FindByUniqueId(document, action.RoomId);
            if (element is not Room room)
            {
                continue;
            }

            if (!RemediationParameterHelper.TryGetTranslationFeet(action, out XYZ translation))
            {
                continue;
            }

            Level? level = document.GetElement(room.LevelId) as Level;
            if (level == null)
            {
                continue;
            }

            XYZ currentCenter = GetRoomCenter(room, level);
            plotCenters.Add(currentCenter);
            XYZ proposedCenter = currentCenter + translation;

            int curves = DrawGhostRoomOutline(document, view, room, level, translation, createdIds);
            if (curves > 0)
            {
                roomsDrawn++;
                DrawShiftArrow(document, view, currentCenter, proposedCenter, createdIds);
                DrawRoomLabel(document, view, proposedCenter, action, room, textTypeId, createdIds);
            }
        }

        if (plotCenters.Count > 0)
        {
            XYZ plotCenter = AveragePoint(plotCenters);
            Level? refLevel = document.GetElement(
                FindByUniqueId(document, ghostActions[0].RoomId) is Room first
                    ? first.LevelId
                    : ElementId.InvalidElementId) as Level;
            if (refLevel != null)
            {
                DrawZoneCompass(document, view, plotCenter, refLevel.Elevation, createdIds);
                if (textTypeId != null)
                {
                    CreateTextNote(
                        document,
                        view,
                        plotCenter + new XYZ(0, 8, 0),
                        "Vastu Compass (N↑)",
                        textTypeId,
                        createdIds,
                        CompassColor);
                }
            }
        }

        transaction.Commit();
        VastuSession.SetGhostElementIds(createdIds);

        return roomsDrawn > 0
            ? GhostRenderResult.Ok(
                $"Advanced ghost design: {roomsDrawn} room(s). " +
                "Cyan = proposed layout, gold arrow = shift, blue = compass.")
            : GhostRenderResult.Fail(
                "Could not draw ghost outlines. Ensure rooms have boundary segments.");
    }

    public static void Clear(Document document)
    {
        PreviewGraphicsHelper.ClearGhost(document);
    }

    private static void DrawShiftArrow(
        Document document,
        View view,
        XYZ from,
        XYZ to,
        List<ElementId> createdIds)
    {
        if (from.DistanceTo(to) < 0.2)
        {
            return;
        }

        Line shaft = Line.CreateBound(from, to);
        ElementId? shaftId = CreateGhostCurve(document, view, shaft, GhostArrowColor, 7);
        if (shaftId != null)
        {
            createdIds.Add(shaftId);
        }

        XYZ dir = (to - from).Normalize();
        XYZ wingA = RotatePlan(dir, Math.PI * 0.75) * 1.2;
        XYZ wingB = RotatePlan(dir, -Math.PI * 0.75) * 1.2;
        XYZ tip = to;

        foreach (XYZ wing in new[] { wingA, wingB })
        {
            Line head = Line.CreateBound(tip, tip + wing);
            ElementId? headId = CreateGhostCurve(document, view, head, GhostArrowColor, 5);
            if (headId != null)
            {
                createdIds.Add(headId);
            }
        }
    }

    private static XYZ RotatePlan(XYZ vector, double radians)
    {
        double cos = Math.Cos(radians);
        double sin = Math.Sin(radians);
        return new XYZ(
            vector.X * cos - vector.Y * sin,
            vector.X * sin + vector.Y * cos,
            0);
    }

    private static void DrawRoomLabel(
        Document document,
        View view,
        XYZ position,
        RemediationAction action,
        Room room,
        ElementId? textTypeId,
        List<ElementId> createdIds)
    {
        string target = action.Parameters.TryGetValue("target_zone", out object? zone)
            ? zone?.ToString() ?? "target"
            : "target";
        string label = $"{room.Name}\n→ {target.Replace('_', ' ')}";
        CreateTextNote(document, view, position, label, textTypeId, createdIds, GhostLineColor);
    }

    private static void DrawZoneCompass(
        Document document,
        View view,
        XYZ center,
        double elevation,
        List<ElementId> createdIds)
    {
        double radius = 6.0;
        var labels = new (string label, double angleDeg)[]
        {
            ("N", 0), ("NE", 45), ("E", 90), ("SE", 135),
            ("S", 180), ("SW", 225), ("W", 270), ("NW", 315),
        };

        XYZ origin = new XYZ(center.X, center.Y, elevation);

        foreach (var item in labels)
        {
            double rad = item.angleDeg * Math.PI / 180.0;
            double dx = Math.Sin(rad) * radius;
            double dy = Math.Cos(rad) * radius;
            XYZ end = new XYZ(origin.X + dx, origin.Y + dy, elevation);
            Line spoke = Line.CreateBound(origin, end);
            ElementId? spokeId = CreateGhostCurve(document, view, spoke, CompassColor, 3);
            if (spokeId != null)
            {
                createdIds.Add(spokeId);
            }
        }

        Line ringN = Line.CreateBound(
            new XYZ(origin.X, origin.Y + radius * 0.6, elevation),
            new XYZ(origin.X, origin.Y + radius, elevation));
        ElementId? ringId = CreateGhostCurve(document, view, ringN, CompassColor, 2);
        if (ringId != null)
        {
            createdIds.Add(ringId);
        }
    }

    private static int DrawGhostRoomOutline(
        Document document,
        View view,
        Room room,
        Level level,
        XYZ translation,
        List<ElementId> createdIds)
    {
        int count = 0;
        SpatialElementBoundaryOptions options = new SpatialElementBoundaryOptions();
        IList<IList<BoundarySegment>>? loops = room.GetBoundarySegments(options);
        if (loops == null)
        {
            return 0;
        }

        double z = level.Elevation;

        foreach (IList<BoundarySegment> loop in loops)
        {
            foreach (BoundarySegment segment in loop)
            {
                Curve curve = segment.GetCurve();
                if (curve == null || !curve.IsBound)
                {
                    continue;
                }

                XYZ start = curve.GetEndPoint(0) + translation;
                XYZ end = curve.GetEndPoint(1) + translation;
                start = new XYZ(start.X, start.Y, z);
                end = new XYZ(end.X, end.Y, z);

                if (start.DistanceTo(end) < 0.05)
                {
                    continue;
                }

                Line line = Line.CreateBound(start, end);
                ElementId? curveId = CreateGhostCurve(document, view, line, GhostLineColor, 8);
                if (curveId != null)
                {
                    createdIds.Add(curveId);
                    count++;
                }
            }
        }

        return count;
    }

    private static void CreateTextNote(
        Document document,
        View view,
        XYZ position,
        string text,
        ElementId? textTypeId,
        List<ElementId> createdIds,
        Color? lineColor = null)
    {
        if (textTypeId == null || view.ViewType != ViewType.FloorPlan && view.ViewType != ViewType.CeilingPlan)
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
                if (lineColor != null)
                {
                    OverrideGraphicSettings ogs = new OverrideGraphicSettings();
                    ogs.SetProjectionLineColor(lineColor);
                    view.SetElementOverrides(note.Id, ogs);
                }

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

    private static ElementId? CreateGhostCurve(
        Document document,
        View view,
        Line line,
        Color color,
        int weight)
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
            ApplyGhostStyle(view, id, color, weight);
        }

        return id;
    }

    private static void ApplyGhostStyle(View view, ElementId elementId, Color color, int weight)
    {
        OverrideGraphicSettings ogs = new OverrideGraphicSettings();
        ogs.SetProjectionLineColor(color);
        ogs.SetProjectionLineWeight(weight);
        view.SetElementOverrides(elementId, ogs);
    }

    private static XYZ AveragePoint(List<XYZ> points)
    {
        if (points.Count == 0)
        {
            return XYZ.Zero;
        }

        double x = points.Average(p => p.X);
        double y = points.Average(p => p.Y);
        double z = points.Average(p => p.Z);
        return new XYZ(x, y, z);
    }

    private static XYZ GetRoomCenter(Room room, Level level)
    {
        LocationPoint? location = room.Location as LocationPoint;
        if (location != null)
        {
            XYZ point = location.Point;
            return new XYZ(point.X, point.Y, level.Elevation);
        }

        BoundingBoxXYZ? box = room.get_BoundingBox(null);
        if (box != null)
        {
            return new XYZ(
                (box.Min.X + box.Max.X) * 0.5,
                (box.Min.Y + box.Max.Y) * 0.5,
                level.Elevation);
        }

        return new XYZ(0, 0, level.Elevation);
    }

    private static Element? FindByUniqueId(Document document, string uniqueId)
    {
        return new FilteredElementCollector(document)
            .WhereElementIsNotElementType()
            .FirstOrDefault(element => element.UniqueId == uniqueId);
    }
}

public class GhostRenderResult
{
    public bool Success { get; init; }
    public string Message { get; init; } = string.Empty;

    public static GhostRenderResult Ok(string message) =>
        new GhostRenderResult { Success = true, Message = message };

    public static GhostRenderResult Fail(string message) =>
        new GhostRenderResult { Success = false, Message = message };
}
