using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Moves room bounding walls and draws zone-alignment guides in the active model.
/// </summary>
public class RoomGeometryAligner
{
    public GeometryApplyResult ApplyBoundaryMove(Document document, Room room, RemediationAction action)
    {
        if (!RemediationParameterHelper.TryGetTranslationFeet(action, out XYZ translation))
        {
            return GeometryApplyResult.Fail("Missing or zero translation for boundary move.");
        }

        ICollection<ElementId> wallIds = GetBoundingWallIds(room);
        if (wallIds.Count == 0)
        {
            return GeometryApplyResult.Fail(
                $"No boundary walls found for room '{room.Name}'. Place room boundaries first.");
        }

        ElementTransformUtils.MoveElements(document, wallIds, translation);
        return GeometryApplyResult.Ok(
            $"Moved {wallIds.Count} boundary wall(s) by ({translation.X:F2}, {translation.Y:F2}) ft.");
    }

    public GeometryApplyResult DrawZoneGuide(
        Document document,
        View? view,
        Room room,
        RemediationAction action)
    {
        if (view == null)
        {
            return GeometryApplyResult.Fail("Active view required to draw zone guide.");
        }

        Level? level = document.GetElement(room.LevelId) as Level;
        if (level == null)
        {
            return GeometryApplyResult.Fail("Room level not found.");
        }

        XYZ start = GetRoomCenter(room, level);
        XYZ end;

        if (RemediationParameterHelper.TryGetPoint2D(action, "target_point", out double tx, out double ty))
        {
            end = new XYZ(tx, ty, level.Elevation);
        }
        else if (RemediationParameterHelper.TryGetTranslationFeet(action, out XYZ translation))
        {
            end = start + translation;
        }
        else
        {
            double length = RemediationParameterHelper.GetGuideLengthFeet(action);
            if (!RemediationParameterHelper.TryGetShiftVector(action, out double dx, out double dy, out _))
            {
                return GeometryApplyResult.Fail("Missing guide direction.");
            }

            end = start + new XYZ(dx * length, dy * length, 0);
        }

        end = new XYZ(end.X, end.Y, level.Elevation);

        if (start.DistanceTo(end) < 0.1)
        {
            return GeometryApplyResult.Fail("Guide length too small.");
        }

        Line line = Line.CreateBound(start, end);
        Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, start);
        SketchPlane sketchPlane = SketchPlane.Create(document, plane);

        if (view.ViewType == ViewType.FloorPlan || view.ViewType == ViewType.CeilingPlan)
        {
            DetailCurve? detail = document.Create.NewDetailCurve(view, line);
            if (detail != null)
            {
                OverrideGuide(view, detail.Id);
            }
        }
        else
        {
            ModelCurve modelCurve = document.Create.NewModelCurve(line, sketchPlane);
            OverrideGuide(view, modelCurve.Id);
        }

        string targetZone = action.Parameters.TryGetValue("target_zone", out object? zone)
            ? zone?.ToString() ?? "target"
            : "target";

        return GeometryApplyResult.Ok($"Drew alignment guide toward {targetZone}.");
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

    private static void OverrideGuide(View view, ElementId curveId)
    {
        OverrideGraphicSettings ogs = new OverrideGraphicSettings();
        ogs.SetProjectionLineColor(new Color(0, 180, 255));
        ogs.SetProjectionLineWeight(5);
        view.SetElementOverrides(curveId, ogs);
    }

    private static ICollection<ElementId> GetBoundingWallIds(Room room)
    {
        var ids = new HashSet<ElementId>();
        SpatialElementBoundaryOptions options = new SpatialElementBoundaryOptions();
        IList<IList<BoundarySegment>>? loops = room.GetBoundarySegments(options);
        if (loops == null)
        {
            return ids;
        }

        foreach (IList<BoundarySegment> loop in loops)
        {
            foreach (BoundarySegment segment in loop)
            {
                ElementId elementId = segment.ElementId;
                if (elementId != ElementId.InvalidElementId)
                {
                    ids.Add(elementId);
                }
            }
        }

        return ids;
    }
}

public class GeometryApplyResult
{
    public bool Success { get; init; }
    public string Message { get; init; } = string.Empty;

    public static GeometryApplyResult Ok(string message) =>
        new GeometryApplyResult { Success = true, Message = message };

    public static GeometryApplyResult Fail(string message) =>
        new GeometryApplyResult { Success = false, Message = message };
}
