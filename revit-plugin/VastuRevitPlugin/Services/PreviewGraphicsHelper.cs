using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;

namespace VastuRevitPlugin.Services;

/// <summary>
/// Safely removes transient ghost/result preview graphics (handles stale ElementIds after undo/delete).
/// </summary>
public static class PreviewGraphicsHelper
{
    public static void ClearAll(Document document)
    {
        ClearGhost(document);
        ClearResult(document);
        ClearGenerated(document);
    }

    public static void ClearGhost(Document document)
    {
        IReadOnlyList<ElementId> ids = VastuSession.GetGhostElementIds();
        SafeDeletePreviewElements(document, ids, "Clear Vastu Ghost Design");
        VastuSession.ClearGhostElements();
    }

    public static void ClearResult(Document document)
    {
        IReadOnlyList<ElementId> ids = VastuSession.GetResultElementIds();
        SafeDeletePreviewElements(document, ids, "Clear Vastu Result Layout");
        VastuSession.ClearResultElements();
    }

    public static void ClearGenerated(Document document)
    {
        IReadOnlyList<ElementId> ids = VastuSession.GetGeneratedElementIds();
        SafeDeletePreviewElements(document, ids, "Clear Vastu Generated Layout");
        VastuSession.ClearGeneratedElements();
    }

    public static IList<ElementId> FilterExistingElementIds(
        Document document,
        IEnumerable<ElementId> ids)
    {
        var existing = new List<ElementId>();
        if (document == null || ids == null)
        {
            return existing;
        }

        foreach (ElementId id in ids)
        {
            if (id == null || id == ElementId.InvalidElementId)
            {
                continue;
            }

            if (document.GetElement(id) != null)
            {
                existing.Add(id);
            }
        }

        return existing;
    }

    private static void SafeDeletePreviewElements(
        Document document,
        IEnumerable<ElementId> ids,
        string transactionName)
    {
        IList<ElementId> existing = FilterExistingElementIds(document, ids);
        if (existing.Count == 0)
        {
            return;
        }

        using Transaction transaction = new Transaction(document, transactionName);
        transaction.Start();
        document.Delete(existing.ToList());
        transaction.Commit();
    }
}
