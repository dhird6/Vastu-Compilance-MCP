using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public class AutocadLayoutExtractor
    {
        public AnalyzeAutocadRequest BuildAnalyzeRequest(Document document)
        {
            Database database = document.Database;
            var payload = new AutocadPayload
            {
                Source = "autocad_layout_2d",
                TrueNorthDegrees = 0.0,
                LayoutName = LayoutManager.Current.CurrentLayout
            };

            using (Transaction tr = database.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(database.BlockTableId, OpenMode.ForRead);
                BlockTableRecord ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                foreach (ObjectId id in ms)
                {
                    Entity entity = tr.GetObject(id, OpenMode.ForRead) as Entity;
                    if (entity == null)
                    {
                        continue;
                    }
                    var converted = ConvertEntity(entity);
                    if (converted != null)
                    {
                        payload.Entities.Add(converted);
                    }
                }

                tr.Commit();
            }

            return new AnalyzeAutocadRequest
            {
                Payload = payload,
                Context = new Dictionary<string, object>
                {
                    { "client", "autocad-plugin" },
                    { "project_id", document.Name ?? "autocad-project" }
                }
            };
        }

        public FloorPlanPayloadDto BuildFloorPlanPayload(Document document)
        {
            AnalyzeAutocadRequest request = BuildAnalyzeRequest(document);
            var elements = new List<FloorPlanElementDto>();
            foreach (AutocadEntity2D entity in request.Payload.Entities)
            {
                if (!string.Equals(entity.EntityType, "room", StringComparison.OrdinalIgnoreCase)
                    || entity.Points == null
                    || entity.Points.Count < 3)
                {
                    continue;
                }

                elements.Add(new FloorPlanElementDto
                {
                    Id = entity.Id,
                    Name = entity.Name,
                    ElementType = "room",
                    Polygon = entity.Points,
                    Metadata = entity.Metadata ?? new Dictionary<string, object>()
                });
            }

            return new FloorPlanPayloadDto
            {
                Source = "direct_json",
                TrueNorthDegrees = request.Payload.TrueNorthDegrees,
                Elements = elements
            };
        }

        private static AutocadEntity2D ConvertEntity(Entity entity)
        {
            string category = ResolveCategory(entity.Layer);
            if (category == null)
            {
                return null;
            }

            List<Point2D> points = ExtractPoints(entity);
            if (points.Count < 2)
            {
                return null;
            }

            string name = entity.Layer + "_" + entity.Handle;
            return new AutocadEntity2D
            {
                Id = entity.Handle.ToString(),
                Name = name,
                EntityType = category,
                Points = points,
                Metadata = new Dictionary<string, object>
                {
                    { "room_type", category == "room" ? InferRoomType(entity.Layer, name) : category },
                    { "layer", entity.Layer },
                    { "entity_class", entity.GetType().Name }
                }
            };
        }

        private static string ResolveCategory(string layerName)
        {
            string layer = (layerName ?? string.Empty).ToLowerInvariant();
            if (layer.Contains("room"))
            {
                return "room";
            }
            if (layer.Contains("wall"))
            {
                return "wall";
            }
            if (layer.Contains("door"))
            {
                return "door";
            }
            if (layer.Contains("window"))
            {
                return "window";
            }
            return null;
        }

        private static string InferRoomType(string layerName, string fallback)
        {
            string layer = (layerName ?? string.Empty).ToLowerInvariant();
            if (layer.Contains("kitchen"))
            {
                return "kitchen";
            }
            if (layer.Contains("master") || layer.Contains("bed"))
            {
                return "master_bedroom";
            }
            if (layer.Contains("pooja"))
            {
                return "pooja";
            }
            if (layer.Contains("toilet"))
            {
                return "toilet";
            }
            if (layer.Contains("living"))
            {
                return "living_room";
            }
            return fallback.ToLowerInvariant().Replace(" ", "_");
        }

        private static List<Point2D> ExtractPoints(Entity entity)
        {
            if (entity is Polyline polyline)
            {
                return ExtractFromPolyline(polyline);
            }

            if (entity is Autodesk.AutoCAD.DatabaseServices.Line line)
            {
                return new List<Point2D>
                {
                    ToPoint2D(line.StartPoint),
                    ToPoint2D(line.EndPoint)
                };
            }

            return new List<Point2D>();
        }

        private static List<Point2D> ExtractFromPolyline(Polyline polyline)
        {
            var points = new List<Point2D>();
            for (int i = 0; i < polyline.NumberOfVertices; i++)
            {
                Point3d p = polyline.GetPoint3dAt(i);
                points.Add(ToPoint2D(p));
            }
            if (polyline.Closed && points.Count > 0)
            {
                points.Add(points[0]);
            }
            return points;
        }

        private static Point2D ToPoint2D(Point3d point)
        {
            return new Point2D { X = point.X, Y = point.Y };
        }
    }
}
