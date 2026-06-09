using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public static class LayoutConstraintEditor
    {
        private static readonly string[] VastuZones =
        {
            "north", "north_east", "east", "south_east",
            "south", "south_west", "west", "north_west"
        };

        public static void RunInteractiveMenu(Document document)
        {
            Editor editor = document.Editor;
            bool running = true;

            while (running)
            {
                PromptKeywordOptions options = new PromptKeywordOptions(
                    Environment.NewLine +
                    "[Vastu] Layout constraints (" + VastuSession.GetLayoutConstraints().Count + " active). Action");
                options.Keywords.Add("Lock");
                options.Keywords.Add("Zone");
                options.Keywords.Add("MaxMove");
                options.Keywords.Add("List");
                options.Keywords.Add("Clear");
                options.Keywords.Add("Done");
                options.Keywords.Default = "Done";
                options.AllowNone = false;

                PromptResult choice = editor.GetKeywords(options);
                if (choice.Status != PromptStatus.OK)
                {
                    return;
                }

                switch (choice.StringResult)
                {
                    case "Lock":
                        AddFixedRoomConstraint(document, editor);
                        break;
                    case "Zone":
                        AddFixedZoneConstraint(document, editor);
                        break;
                    case "MaxMove":
                        AddMaxMoveConstraint(document, editor);
                        break;
                    case "List":
                        PrintConstraints(editor);
                        break;
                    case "Clear":
                        VastuSession.ClearLayoutConstraints();
                        editor.WriteMessage(Environment.NewLine + "[Vastu] Cleared all layout constraints.");
                        break;
                    default:
                        running = false;
                        break;
                }
            }
        }

        private static void AddFixedRoomConstraint(Document document, Editor editor)
        {
            string roomId = PromptRoomEntityId(document, editor, "Select room polyline to lock in place");
            if (string.IsNullOrWhiteSpace(roomId))
            {
                return;
            }

            VastuSession.AddLayoutConstraint(new UserLayoutConstraintDto
            {
                ConstraintId = "fixed-room-" + roomId,
                Kind = "fixed_room",
                RoomId = roomId,
                Reason = "Locked from AutoCAD UI"
            });
            editor.WriteMessage(Environment.NewLine + "[Vastu] Locked room " + roomId + ".");
        }

        private static void AddFixedZoneConstraint(Document document, Editor editor)
        {
            string roomId = PromptRoomEntityId(document, editor, "Select room to pin to a Vastu zone");
            if (string.IsNullOrWhiteSpace(roomId))
            {
                return;
            }

            string zone = PromptZone(editor);
            if (string.IsNullOrWhiteSpace(zone))
            {
                return;
            }

            VastuSession.AddLayoutConstraint(new UserLayoutConstraintDto
            {
                ConstraintId = "fixed-zone-" + roomId,
                Kind = "fixed_zone",
                RoomId = roomId,
                Zone = zone,
                Reason = "Zone pinned from AutoCAD UI"
            });
            editor.WriteMessage(Environment.NewLine + "[Vastu] Room " + roomId + " pinned to " + zone + ".");
        }

        private static void AddMaxMoveConstraint(Document document, Editor editor)
        {
            string roomId = PromptRoomEntityId(document, editor, "Select room to limit movement");
            if (string.IsNullOrWhiteSpace(roomId))
            {
                return;
            }

            PromptDoubleOptions distanceOptions = new PromptDoubleOptions(
                Environment.NewLine + "[Vastu] Maximum move distance (feet)");
            distanceOptions.AllowNegative = false;
            distanceOptions.AllowZero = false;
            distanceOptions.DefaultValue = 5.0;

            PromptDoubleResult distanceResult = editor.GetDouble(distanceOptions);
            if (distanceResult.Status != PromptStatus.OK)
            {
                return;
            }

            VastuSession.AddLayoutConstraint(new UserLayoutConstraintDto
            {
                ConstraintId = "max-move-" + roomId,
                Kind = "max_move",
                RoomId = roomId,
                MaxTranslationFeet = distanceResult.Value,
                Reason = "Max move set from AutoCAD UI"
            });
            editor.WriteMessage(
                Environment.NewLine +
                "[Vastu] Room " + roomId + " limited to " + distanceResult.Value.ToString("0.0") + " ft.");
        }

        private static string PromptRoomEntityId(Document document, Editor editor, string message)
        {
            PromptEntityOptions entityOptions = new PromptEntityOptions(Environment.NewLine + message);
            entityOptions.SetRejectMessage(Environment.NewLine + "[Vastu] Select a closed room polyline.");
            entityOptions.AddAllowedClass(typeof(Polyline), true);
            entityOptions.AddAllowedClass(typeof(Polyline2d), true);

            PromptEntityResult entityResult = editor.GetEntity(entityOptions);
            if (entityResult.Status != PromptStatus.OK)
            {
                return null;
            }

            using (Transaction tr = document.Database.TransactionManager.StartTransaction())
            {
                Entity entity = tr.GetObject(entityResult.ObjectId, OpenMode.ForRead) as Entity;
                tr.Commit();
                return entity?.Handle.ToString();
            }
        }

        private static string PromptZone(Editor editor)
        {
            PromptKeywordOptions zoneOptions = new PromptKeywordOptions(
                Environment.NewLine + "[Vastu] Choose Vastu zone");
            foreach (string zone in VastuZones)
            {
                zoneOptions.Keywords.Add(zone);
            }

            zoneOptions.AllowNone = false;
            PromptResult zoneResult = editor.GetKeywords(zoneOptions);
            return zoneResult.Status == PromptStatus.OK ? zoneResult.StringResult : null;
        }

        private static void PrintConstraints(Editor editor)
        {
            IReadOnlyList<UserLayoutConstraintDto> constraints = VastuSession.GetLayoutConstraints();
            if (constraints.Count == 0)
            {
                editor.WriteMessage(Environment.NewLine + "[Vastu] No layout constraints configured.");
                return;
            }

            editor.WriteMessage(Environment.NewLine + "[Vastu] Active layout constraints:");
            foreach (UserLayoutConstraintDto constraint in constraints)
            {
                editor.WriteMessage(
                    Environment.NewLine +
                    "  - " + constraint.Kind + " | room=" + (constraint.RoomId ?? "-") +
                    " | zone=" + (constraint.Zone ?? "-") +
                    " | max_ft=" + (constraint.MaxTranslationFeet?.ToString("0.0") ?? "-"));
            }
        }
    }
}
