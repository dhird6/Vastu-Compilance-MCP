"""IFC room graph extraction via IfcOpenShell."""

from __future__ import annotations

from pathlib import Path

from app.models.schemas import (
    BoundingBox3D,
    Point3D,
    RevitElement3D,
    RevitElementType,
    RevitModelPayload,
)


def parse_ifc_model(file_path: Path, *, true_north_degrees: float = 0.0) -> RevitModelPayload:
    """
    Extract IfcSpace elements as room footprints for Vastu analysis.

    Requires ifcopenshell (optional dependency).
    """
    try:
        import ifcopenshell
        import ifcopenshell.geom
    except ImportError as exc:
        raise RuntimeError(
            "ifcopenshell is required for IFC parsing. pip install ifcopenshell"
        ) from exc

    model = ifcopenshell.open(str(file_path))
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    elements: list[RevitElement3D] = []
    for index, space in enumerate(model.by_type("IfcSpace")):
        shape = ifcopenshell.geom.create_shape(settings, space)
        verts = shape.geometry.verts
        if len(verts) < 9:
            continue
        xs = verts[0::3]
        ys = verts[1::3]
        zs = verts[2::3]
        bbox = BoundingBox3D(
            min=Point3D(x=min(xs), y=min(ys), z=min(zs)),
            max=Point3D(x=max(xs), y=max(ys), z=max(zs)),
        )
        name = getattr(space, "Name", None) or f"Space-{index}"
        long_name = getattr(space, "LongName", None) or name
        elements.append(
            RevitElement3D(
                id=str(space.GlobalId),
                name=str(long_name),
                element_type=RevitElementType.room,
                bounding_box=bbox,
                metadata={"room_type": str(name).lower().replace(" ", "_"), "source": "ifc"},
            )
        )

    return RevitModelPayload(true_north_degrees=true_north_degrees, elements=elements)
