using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public static class LayoutConstraintManager
{
    private static readonly string[] VastuZones =
    {
        "north", "north_east", "east", "south_east",
        "south", "south_west", "west", "north_west"
    };

    public static void ShowConfigurationDialog(UIDocument uiDocument)
    {
        bool running = true;
        while (running)
        {
            TaskDialog dialog = new TaskDialog("Layout Constraints")
            {
                MainInstruction = "Configure constraints before generating a new Vastu layout",
                MainContent =
                    $"{VastuSession.GetLayoutConstraints().Count} active constraint(s).\n\n" +
                    "Locked rooms and pinned zones are preserved during layout generation.",
            };

            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, "Lock rooms in place");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, "Pin room to Vastu zone");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, "Limit room movement (max feet)");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink4, "Show current constraints");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink5, "Clear all constraints");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink6, "Done");

            TaskDialogResult result = dialog.Show();
            switch (result)
            {
                case TaskDialogResult.CommandLink1:
                    LockSelectedRooms(uiDocument);
                    break;
                case TaskDialogResult.CommandLink2:
                    PinRoomToZone(uiDocument);
                    break;
                case TaskDialogResult.CommandLink3:
                    LimitRoomMovement(uiDocument);
                    break;
                case TaskDialogResult.CommandLink4:
                    ShowConstraintSummary();
                    break;
                case TaskDialogResult.CommandLink5:
                    VastuSession.ClearLayoutConstraints();
                    TaskDialog.Show("Layout Constraints", "All constraints cleared.");
                    break;
                default:
                    running = false;
                    break;
            }
        }
    }

    private static void LockSelectedRooms(UIDocument uiDocument)
    {
        IList<Reference>? picked = PickRooms(uiDocument, "Pick rooms to lock in place");
        if (picked == null || picked.Count == 0)
        {
            return;
        }

        Document document = uiDocument.Document;
        int added = 0;
        foreach (Reference reference in picked)
        {
            Element? element = document.GetElement(reference);
            if (element == null)
            {
                continue;
            }

            VastuSession.AddLayoutConstraint(new UserLayoutConstraintDto
            {
                ConstraintId = "fixed-room-" + element.UniqueId,
                Kind = "fixed_room",
                RoomId = element.UniqueId,
                Reason = "Locked from Revit UI",
            });
            added++;
        }

        TaskDialog.Show("Layout Constraints", $"Locked {added} room(s).");
    }

    private static void PinRoomToZone(UIDocument uiDocument)
    {
        IList<Reference>? picked = PickRooms(uiDocument, "Pick one room to pin to a Vastu zone", single: true);
        if (picked == null || picked.Count == 0)
        {
            return;
        }

        Element? room = uiDocument.Document.GetElement(picked[0]);
        if (room == null)
        {
            return;
        }

        string? zone = PromptZone();
        if (string.IsNullOrWhiteSpace(zone))
        {
            return;
        }

        VastuSession.AddLayoutConstraint(new UserLayoutConstraintDto
        {
            ConstraintId = "fixed-zone-" + room.UniqueId,
            Kind = "fixed_zone",
            RoomId = room.UniqueId,
            Zone = zone,
            Reason = "Zone pinned from Revit UI",
        });

        TaskDialog.Show("Layout Constraints", $"Pinned {room.Name} to {zone.Replace('_', ' ')}.");
    }

    private static void LimitRoomMovement(UIDocument uiDocument)
    {
        IList<Reference>? picked = PickRooms(uiDocument, "Pick room to limit movement", single: true);
        if (picked == null || picked.Count == 0)
        {
            return;
        }

        Element? room = uiDocument.Document.GetElement(picked[0]);
        if (room == null)
        {
            return;
        }

        double? maxFeet = PromptMaxMoveFeet();
        if (maxFeet == null)
        {
            return;
        }

        VastuSession.AddLayoutConstraint(new UserLayoutConstraintDto
        {
            ConstraintId = "max-move-" + room.UniqueId,
            Kind = "max_move",
            RoomId = room.UniqueId,
            MaxTranslationFeet = maxFeet,
            Reason = "Max move set from Revit UI",
        });

        TaskDialog.Show("Layout Constraints", $"Limited {room.Name} to {maxFeet:0.0} ft movement.");
    }

    private static IList<Reference>? PickRooms(UIDocument uiDocument, string prompt, bool single = false)
    {
        try
        {
            ISelectionFilter filter = new RoomSelectionFilter();
            if (single)
            {
                Reference reference = uiDocument.Selection.PickObject(ObjectType.Element, filter, prompt);
                return new List<Reference> { reference };
            }

            return uiDocument.Selection.PickObjects(ObjectType.Element, filter, prompt);
        }
        catch (Autodesk.Revit.Exceptions.OperationCanceledException)
        {
            return null;
        }
    }

    private static string? PromptZone()
    {
        TaskDialog dialog = new TaskDialog("Choose Vastu Zone")
        {
            MainInstruction = "Select the zone this room must stay in",
        };

        for (int index = 0; index < VastuZones.Length; index++)
        {
            TaskDialogCommandLinkId linkId = (TaskDialogCommandLinkId)((int)TaskDialogCommandLinkId.CommandLink1 + index);
            dialog.AddCommandLink(linkId, VastuZones[index].Replace('_', ' '));
        }

        TaskDialogResult result = dialog.Show();
        int selected = (int)result - (int)TaskDialogResult.CommandLink1;
        if (selected < 0 || selected >= VastuZones.Length)
        {
            return null;
        }

        return VastuZones[selected];
    }

    private static double? PromptMaxMoveFeet()
    {
        TaskDialog dialog = new TaskDialog("Maximum Move Distance")
        {
            MainInstruction = "How far may this room move during layout generation?",
        };
        dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, "3 feet");
        dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, "5 feet");
        dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, "8 feet");
        dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink4, "10 feet");

        TaskDialogResult result = dialog.Show();
        return result switch
        {
            TaskDialogResult.CommandLink1 => 3.0,
            TaskDialogResult.CommandLink2 => 5.0,
            TaskDialogResult.CommandLink3 => 8.0,
            TaskDialogResult.CommandLink4 => 10.0,
            _ => null,
        };
    }

    private static void ShowConstraintSummary()
    {
        IReadOnlyList<UserLayoutConstraintDto> constraints = VastuSession.GetLayoutConstraints();
        if (constraints.Count == 0)
        {
            TaskDialog.Show("Layout Constraints", "No constraints configured.");
            return;
        }

        StringBuilder builder = new StringBuilder();
        foreach (UserLayoutConstraintDto constraint in constraints)
        {
            builder.AppendLine(
                $"- {constraint.Kind} | room={constraint.RoomId ?? "-"} | zone={constraint.Zone ?? "-"} | max_ft={constraint.MaxTranslationFeet?.ToString("0.0") ?? "-"}");
        }

        TaskDialog.Show("Layout Constraints", builder.ToString());
    }

    private sealed class RoomSelectionFilter : ISelectionFilter
    {
        public bool AllowElement(Element elem) => elem is Room;

        public bool AllowReference(Reference reference, XYZ position) => true;
    }
}
