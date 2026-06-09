using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public class ResultLayoutRenderer
    {
        public const string ResultLayerName = "VASTU_RESULT";
        public const string ChangedLayerName = "VASTU_RESULT_CHANGED";

        public ResultRenderResult Show(Document document, CorrectedLayoutResult correctedLayout)
        {
            Clear(document);

            if (correctedLayout?.CorrectedPayload?.Elements == null
                || correctedLayout.CorrectedPayload.Elements.Count == 0)
            {
                return ResultRenderResult.Fail("No corrected layout data available.");
            }

            var changedIds = new HashSet<string>(
                correctedLayout.ChangesApplied
                    .Where(change => change != null && !string.IsNullOrWhiteSpace(change.RoomId))
                    .Select(change => change.RoomId),
                StringComparer.OrdinalIgnoreCase);

            Database database = document.Database;
            var createdHandles = new List<string>();
            int roomsDrawn = 0;
            int changedDrawn = 0;

            using (DocumentLock docLock = document.LockDocument())
            using (Transaction tr = database.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(database.BlockTableId, OpenMode.ForRead);
                BlockTableRecord ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                EnsureLayer(tr, database, ResultLayerName, Color.FromColorIndex(ColorMethod.ByAci, 3));
                EnsureLayer(tr, database, ChangedLayerName, Color.FromColorIndex(ColorMethod.ByAci, 92));

                foreach (FloorPlanElementDto element in correctedLayout.CorrectedPayload.Elements)
                {
                    if (!string.Equals(element.ElementType, "room", StringComparison.OrdinalIgnoreCase)
                        || element.Polygon == null
                        || element.Polygon.Count < 3)
                    {
                        continue;
                    }

                    bool changed = changedIds.Contains(element.Id) || IsMetadataCorrected(element.Metadata);
                    string layer = changed ? ChangedLayerName : ResultLayerName;
                    ObjectId polylineId = CreateRoomPolyline(tr, ms, element.Polygon, layer);
                    if (!polylineId.IsNull)
                    {
                        Entity entity = tr.GetObject(polylineId, OpenMode.ForRead) as Entity;
                        if (entity != null)
                        {
                            createdHandles.Add(entity.Handle.ToString());
                            roomsDrawn++;
                            if (changed)
                            {
                                changedDrawn++;
                            }
                        }
                    }
                }

                tr.Commit();
            }

            VastuSession.SetResultEntityHandles(createdHandles);

            if (roomsDrawn == 0)
            {
                return ResultRenderResult.Fail("Could not draw result layout polylines.");
            }

            return ResultRenderResult.Ok(
                "Result layout: " + roomsDrawn + " room(s), " + changedDrawn + " corrected. " +
                "Score " + correctedLayout.OriginalComplianceScore.ToString("0.0") + "% -> " +
                correctedLayout.CorrectedComplianceScore.ToString("0.0") + "%.");
        }

        public static void Clear(Document document)
        {
            IReadOnlyList<string> handles = VastuSession.GetResultEntityHandles();
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

            VastuSession.ClearResultEntities();
        }

        private static ObjectId CreateRoomPolyline(
            Transaction tr,
            BlockTableRecord modelSpace,
            List<Point2D> polygon,
            string layer)
        {
            Polyline polyline = new Polyline();
            for (int index = 0; index < polygon.Count; index++)
            {
                polyline.AddVertexAt(index, new Point2d(polygon[index].X, polygon[index].Y), 0, 0, 0);
            }

            polyline.Closed = true;
            polyline.Layer = layer;
            ObjectId polylineId = modelSpace.AppendEntity(polyline);
            tr.AddNewlyCreatedDBObject(polyline, true);
            return polylineId;
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

        private static bool IsMetadataCorrected(Dictionary<string, object> metadata)
        {
            if (metadata == null || !metadata.TryGetValue("vastu_corrected", out object value))
            {
                return false;
            }

            return value is bool flag && flag;
        }
    }

    public class ResultRenderResult
    {
        public bool Success { get; set; }
        public string Message { get; set; }

        public static ResultRenderResult Ok(string message)
        {
            return new ResultRenderResult { Success = true, Message = message };
        }

        public static ResultRenderResult Fail(string message)
        {
            return new ResultRenderResult { Success = false, Message = message };
        }
    }
}
