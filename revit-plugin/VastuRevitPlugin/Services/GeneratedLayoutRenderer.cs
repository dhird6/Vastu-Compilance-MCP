using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Draws a new Vastu-compliant 2D layout from server Revit I/O export (non-destructive).
/// </summary>
public class GeneratedLayoutRenderer
{
    private static readonly Color RoomColor = new Color(80, 160, 255);
    private static readonly Color PlotColor = new Color(255, 120, 80);
    private static readonly Color LabelColor = new Color(80, 160, 255);

    public ResultRenderResult Show(Document document, View? view, RevitLayoutExportDto layoutExport)
    {
        Clear(document);

        if (view == null)
        {
            return ResultRenderResult.Fail("Open a floor plan view to show the generated layout.");
        }

        if (layoutExport?.Rooms == null || layoutExport.Rooms.Count == 0)
        {
            return ResultRenderResult.Fail("No generated layout rooms in the last response.");
        }

        var createdIds = new List<ElementId>();
        int roomsDrawn = 0;
        double elevation = view is ViewPlan plan && plan.GenLevel != null ? plan.GenLevel.Elevation : 0.0;

        using Transaction transaction = new Transaction(document, "Vastu Generated Layout");
        transaction.Start();

        ElementId? textTypeId = GetDefaultTextNoteType(document);

        if (layoutExport.PlotBoundary.Count >= 3)
        {
            DrawPolygon(document, view, layoutExport.PlotBoundary, elevation, PlotColor, 7, createdIds);
        }

        foreach (RevitLayoutRoomDto room in layoutExport.Rooms)
        {
            if (room.Polygon.Count < 3)
            {
                continue;
            }

            int segments = DrawPolygon(document, view, room.Polygon, elevation, RoomColor, 8, createdIds);
            if (segments > 0)
            {
                roomsDrawn++;
                DrawRoomLabel(document, view, room, elevation, textTypeId, createdIds);
            }
        }

        transaction.Commit();
        VastuSession.SetGeneratedElementIds(createdIds);

        if (roomsDrawn == 0)
        {
            return ResultRenderResult.Fail("Could not draw generated layout polygons.");
        }

        return ResultRenderResult.Ok(
            $"Generated layout: {roomsDrawn} room(s). " +
            $"Score {layoutExport.OriginalComplianceScore:0.0}% → {layoutExport.ComplianceScore:0.0}%.");
    }

    public static void Clear(Document document)
    {
        PreviewGraphicsHelper.ClearGenerated(document);
    }

    private static int DrawPolygon(
        Document document,
        View view,
        List<Point2DDto> polygon,
        double elevation,
        Color color,
        int weight,
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
            ElementId? curveId = CreateCurve(document, view, line, color, weight);
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
        RevitLayoutRoomDto room,
        double elevation,
        ElementId? textTypeId,
        List<ElementId> createdIds)
    {
        if (textTypeId == null || room.Polygon.Count == 0)
        {
            return;
        }

        double cx = room.Polygon.Average(point => point.X);
        double cy = room.Polygon.Average(point => point.Y);
        string zone = room.Zone.Replace('_', ' ');
        string label = $"{room.Name}\n{zone}";

        try
        {
            TextNoteOptions options = new TextNoteOptions(textTypeId)
            {
                HorizontalAlignment = HorizontalTextAlignment.Center,
            };
            TextNote? note = TextNote.Create(document, view.Id, new XYZ(cx, cy, elevation), label, options);
            if (note != null)
            {
                OverrideGraphicSettings ogs = new OverrideGraphicSettings();
                ogs.SetProjectionLineColor(LabelColor);
                view.SetElementOverrides(note.Id, ogs);
                createdIds.Add(note.Id);
            }
        }
        catch
        {
            // Text notes optional
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

    private static ElementId? CreateCurve(
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
            OverrideGraphicSettings ogs = new OverrideGraphicSettings();
            ogs.SetProjectionLineColor(color);
            ogs.SetProjectionLineWeight(weight);
            view.SetElementOverrides(id, ogs);
        }

        return id;
    }
}
