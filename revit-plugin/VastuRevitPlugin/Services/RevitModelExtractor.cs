using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public class RevitModelExtractor
{
    public RevitAnalyzeRequest BuildAnalyzeRequest(Document document)
    {
        var payload = new RevitPayload
        {
            Source = "revit_3d",
            TrueNorthDegrees = ResolveTrueNorthDegrees(document),
            Levels = CollectLevels(document),
            Elements = CollectElements(document)
        };

        return new RevitAnalyzeRequest
        {
            Payload = payload,
            Context = new Dictionary<string, object>
            {
                { "client", "revit-plugin" },
                { "project_id", document.ProjectInformation?.Name ?? "unknown" },
                { "document_title", document.Title ?? "untitled" }
            }
        };
    }

    private static List<string> CollectLevels(Document document)
    {
        return new FilteredElementCollector(document)
            .OfClass(typeof(Level))
            .Cast<Level>()
            .Select(level => level.Name)
            .Distinct()
            .ToList();
    }

    private static List<RevitElement3D> CollectElements(Document document)
    {
        var elements = new List<RevitElement3D>();
        elements.AddRange(CollectRooms(document));
        elements.AddRange(CollectByCategory(document, BuiltInCategory.OST_Walls, "wall", "wall_type"));
        elements.AddRange(CollectByCategory(document, BuiltInCategory.OST_Doors, "door", "family"));
        elements.AddRange(CollectByCategory(document, BuiltInCategory.OST_Windows, "window", "family"));
        return elements;
    }

    private static IEnumerable<RevitElement3D> CollectRooms(Document document)
    {
        var collector = new FilteredElementCollector(document)
            .OfCategory(BuiltInCategory.OST_Rooms)
            .WhereElementIsNotElementType();

        foreach (Element element in collector)
        {
            if (element is not Room room)
            {
                continue;
            }

            BoundingBoxXYZ? box = room.get_BoundingBox(null);
            if (box == null)
            {
                continue;
            }

            var metadata = new Dictionary<string, object>
            {
                { "room_type", InferRoomType(room) },
                { "category", BuiltInCategory.OST_Rooms.ToString() },
                { "projection_mode", "room_boundary" },
                { "footprint_polygon", ExtractRoomFootprint(room) }
            };

            yield return new RevitElement3D
            {
                Id = room.UniqueId,
                Name = string.IsNullOrWhiteSpace(room.Name) ? "room" : room.Name,
                ElementType = "room",
                BoundingBox = ToBoundingBox(box),
                Metadata = metadata
            };
        }
    }

    private static List<Dictionary<string, double>> ExtractRoomFootprint(Room room)
    {
        var points = new List<Dictionary<string, double>>();
        SpatialElementBoundaryOptions options = new SpatialElementBoundaryOptions();
        IList<IList<BoundarySegment>>? loops = room.GetBoundarySegments(options);
        if (loops == null || loops.Count == 0)
        {
            return points;
        }

        foreach (BoundarySegment segment in loops[0])
        {
            Curve curve = segment.GetCurve();
            XYZ end = curve.GetEndPoint(1);
            points.Add(new Dictionary<string, double> { { "x", end.X }, { "y", end.Y } });
        }

        return points;
    }

    private static IEnumerable<RevitElement3D> CollectByCategory(
        Document document,
        BuiltInCategory category,
        string elementType,
        string metaKey)
    {
        var collector = new FilteredElementCollector(document)
            .OfCategory(category)
            .WhereElementIsNotElementType();

        foreach (Element element in collector)
        {
            BoundingBoxXYZ? box = element.get_BoundingBox(null);
            if (box == null)
            {
                continue;
            }

            yield return new RevitElement3D
            {
                Id = element.UniqueId,
                Name = string.IsNullOrWhiteSpace(element.Name) ? elementType : element.Name,
                ElementType = elementType,
                BoundingBox = ToBoundingBox(box),
                Metadata = new Dictionary<string, object>
                {
                    { metaKey, InferTypeName(element, elementType) },
                    { "category", category.ToString() }
                }
            };
        }
    }

    private static BoundingBox3D ToBoundingBox(BoundingBoxXYZ box)
    {
        return new BoundingBox3D
        {
            Min = new Point3D { X = box.Min.X, Y = box.Min.Y, Z = box.Min.Z },
            Max = new Point3D { X = box.Max.X, Y = box.Max.Y, Z = box.Max.Z }
        };
    }

    private static double ResolveTrueNorthDegrees(Document document)
    {
        ProjectLocation? location = document.ActiveProjectLocation;
        if (location == null)
        {
            return 0.0;
        }

        ProjectPosition? origin = location.GetProjectPosition(XYZ.Zero);
        if (origin == null)
        {
            return 0.0;
        }

        return origin.Angle * (180.0 / Math.PI);
    }

    private static string InferRoomType(Room room)
    {
        Parameter? roomName = room.get_Parameter(BuiltInParameter.ROOM_NAME);
        string name = roomName?.AsString() ?? room.Name ?? "room";
        return NormalizeRoomType(name);
    }

    private static string InferTypeName(Element element, string fallback)
    {
        if (element is SpatialElement spatialElement)
        {
            Parameter? roomName = spatialElement.get_Parameter(BuiltInParameter.ROOM_NAME);
            if (roomName != null && roomName.HasValue)
            {
                return NormalizeRoomType(roomName.AsString() ?? fallback);
            }
        }

        ElementId typeId = element.GetTypeId();
        if (typeId != ElementId.InvalidElementId)
        {
            Element? typeElement = element.Document.GetElement(typeId);
            if (typeElement != null && !string.IsNullOrWhiteSpace(typeElement.Name))
            {
                return typeElement.Name.Trim().ToLowerInvariant().Replace(" ", "_");
            }
        }

        return fallback;
    }

    private static string NormalizeRoomType(string name)
    {
        string lower = name.Trim().ToLowerInvariant();
        if (lower.Contains("kitchen")) return "kitchen";
        if (lower.Contains("master") && lower.Contains("bed")) return "master_bedroom";
        if (lower.Contains("bed")) return "master_bedroom";
        if (lower.Contains("pooja") || lower.Contains("puja")) return "pooja";
        if (lower.Contains("toilet") || lower.Contains("bath")) return "toilet";
        if (lower.Contains("living")) return "living_room";
        if (lower.Contains("entrance") || lower.Contains("foyer")) return "entrance";
        if (lower.Contains("stair")) return "staircase";
        return lower.Replace(" ", "_");
    }
}
