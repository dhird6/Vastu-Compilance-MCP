using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public class GeneratedLayoutRenderer
    {
        public const string GeneratedRoomLayer = "VASTU_GENERATED";
        public const string GeneratedPlotLayer = "VASTU_GENERATED_PLOT";
        public const string GeneratedWallLayer = "VASTU_GENERATED_WALL";

        public ResultRenderResult Show(Document document, AutocadLayoutExport autocadExport)
        {
            Clear(document);

            if (autocadExport?.DxfBlueprint?.Entities == null || autocadExport.DxfBlueprint.Entities.Count == 0)
            {
                return ResultRenderResult.Fail("No generated layout blueprint available.");
            }

            Database database = document.Database;
            var createdHandles = new List<string>();
            int entitiesDrawn = 0;

            using (DocumentLock docLock = document.LockDocument())
            using (Transaction tr = database.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(database.BlockTableId, OpenMode.ForRead);
                BlockTableRecord ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                EnsureLayer(tr, database, GeneratedRoomLayer, Color.FromColorIndex(ColorMethod.ByAci, 150));
                EnsureLayer(tr, database, GeneratedPlotLayer, Color.FromColorIndex(ColorMethod.ByAci, 1));
                EnsureLayer(tr, database, GeneratedWallLayer, Color.FromColorIndex(ColorMethod.ByAci, 8));

                foreach (DxfEntity entity in autocadExport.DxfBlueprint.Entities)
                {
                    string layer = MapLayer(entity.Layer);
                    ObjectId id = ObjectId.Null;

                    if (string.Equals(entity.Type, "LWPOLYLINE", StringComparison.OrdinalIgnoreCase)
                        && entity.Points != null
                        && entity.Points.Count >= 3)
                    {
                        id = CreatePolyline(tr, ms, entity.Points, layer, entity.Closed);
                    }
                    else if (string.Equals(entity.Type, "LINE", StringComparison.OrdinalIgnoreCase)
                        && entity.Start != null
                        && entity.End != null)
                    {
                        id = CreateLine(tr, ms, entity.Start, entity.End, layer);
                    }

                    if (!id.IsNull)
                    {
                        Entity created = tr.GetObject(id, OpenMode.ForRead) as Entity;
                        if (created != null)
                        {
                            createdHandles.Add(created.Handle.ToString());
                            entitiesDrawn++;
                        }
                    }
                }

                tr.Commit();
            }

            VastuSession.SetGeneratedEntityHandles(createdHandles);

            if (entitiesDrawn == 0)
            {
                return ResultRenderResult.Fail("Could not draw generated layout entities.");
            }

            return ResultRenderResult.Ok(
                "Generated Vastu layout: " + entitiesDrawn + " entity/entities. " +
                "Score " + autocadExport.OriginalComplianceScore.ToString("0.0") + "% -> " +
                autocadExport.ComplianceScore.ToString("0.0") + "%.");
        }

        public static void Clear(Document document)
        {
            IReadOnlyList<string> handles = VastuSession.GetGeneratedEntityHandles();
            if (handles == null || handles.Count == 0)
            {
                return;
            }

            Database database = document.Database;
            using (DocumentLock docLock = document.LockDocument())
            using (Transaction tr = database.TransactionManager.StartTransaction())
            {
                foreach (string handleText in handles)
                {
                    try
                    {
                        Handle handle = new Handle(Convert.ToInt64(handleText, 16));
                        ObjectId id = database.GetObjectId(false, handle, 0);
                        if (id.IsNull)
                        {
                            continue;
                        }

                        Entity entity = tr.GetObject(id, OpenMode.ForWrite) as Entity;
                        entity?.Erase();
                    }
                    catch
                    {
                        // Skip stale handles
                    }
                }

                tr.Commit();
            }

            VastuSession.ClearGeneratedEntities();
        }

        private static string MapLayer(string sourceLayer)
        {
            if (string.Equals(sourceLayer, "VASTU_PLOT", StringComparison.OrdinalIgnoreCase))
            {
                return GeneratedPlotLayer;
            }
            if (string.Equals(sourceLayer, "VASTU_WALLS", StringComparison.OrdinalIgnoreCase))
            {
                return GeneratedWallLayer;
            }
            return GeneratedRoomLayer;
        }

        private static ObjectId CreatePolyline(
            Transaction tr,
            BlockTableRecord modelSpace,
            List<Point2D> points,
            string layer,
            bool closed)
        {
            Polyline polyline = new Polyline();
            for (int index = 0; index < points.Count; index++)
            {
                polyline.AddVertexAt(index, new Point2d(points[index].X, points[index].Y), 0, 0, 0);
            }

            polyline.Closed = closed;
            polyline.Layer = layer;
            ObjectId polylineId = modelSpace.AppendEntity(polyline);
            tr.AddNewlyCreatedDBObject(polyline, true);
            return polylineId;
        }

        private static ObjectId CreateLine(
            Transaction tr,
            BlockTableRecord modelSpace,
            Point2D start,
            Point2D end,
            string layer)
        {
            Line line = new Line(
                new Point3d(start.X, start.Y, 0),
                new Point3d(end.X, end.Y, 0));
            line.Layer = layer;
            ObjectId lineId = modelSpace.AppendEntity(line);
            tr.AddNewlyCreatedDBObject(line, true);
            return lineId;
        }

        private static void EnsureLayer(Transaction tr, Database database, string layerName, Color color)
        {
            LayerTable lt = (LayerTable)tr.GetObject(database.LayerTableId, OpenMode.ForRead);
            if (lt.Has(layerName))
            {
                return;
            }

            lt.UpgradeOpen();
            LayerTableRecord layer = new LayerTableRecord
            {
                Name = layerName,
                Color = color,
            };
            lt.Add(layer);
            tr.AddNewlyCreatedDBObject(layer, true);
            lt.DowngradeOpen();
        }
    }
}
