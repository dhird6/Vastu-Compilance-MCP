"""Export GeneratedLayoutDocument to DXF-compatible structure (ezdxf optional)."""

from __future__ import annotations

from app.models.schemas import GeneratedLayoutDocument, Point2D


def export_layout_to_dxf_dict(layout: GeneratedLayoutDocument) -> dict[str, object]:
    """
    Return a serializable DXF blueprint the plugin can write with ezdxf.

    Does not write to disk — callers persist the artifact separately.
    """
    layers = {
        "VASTU_ROOMS": {"color": 3},
        "VASTU_WALLS": {"color": 8},
        "VASTU_PLOT": {"color": 1},
    }
    entities: list[dict[str, object]] = []

    entities.append(
        {
            "type": "LWPOLYLINE",
            "layer": "VASTU_PLOT",
            "closed": True,
            "points": _coords(layout.metadata.plot_boundary),
        }
    )

    for room in layout.rooms:
        entities.append(
            {
                "type": "LWPOLYLINE",
                "layer": "VASTU_ROOMS",
                "closed": True,
                "points": _coords(room.polygon),
                "metadata": {
                    "room_id": room.room_id,
                    "room_type": room.room_type,
                    "zone": room.zone,
                },
            }
        )

    for wall in layout.walls:
        if len(wall.polygon) >= 2:
            entities.append(
                {
                    "type": "LINE",
                    "layer": "VASTU_WALLS",
                    "start": {"x": wall.polygon[0].x, "y": wall.polygon[0].y},
                    "end": {"x": wall.polygon[1].x, "y": wall.polygon[1].y},
                }
            )

    return {
        "format": "dxf_blueprint_v1",
        "units": layout.metadata.units,
        "layers": layers,
        "entities": entities,
    }


def write_layout_dxf(layout: GeneratedLayoutDocument, output_path: str) -> None:
    """Write DXF file when ezdxf is installed."""
    try:
        import ezdxf
    except ImportError as exc:
        raise RuntimeError("ezdxf is required for DXF export. pip install ezdxf") from exc

    blueprint = export_layout_to_dxf_dict(layout)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    for layer_name, props in blueprint["layers"].items():
        doc.layers.add(layer_name, color=int(props["color"]))

    for entity in blueprint["entities"]:
        entity_type = entity["type"]
        layer = str(entity["layer"])
        if entity_type == "LWPOLYLINE":
            points = [(p["x"], p["y"]) for p in entity["points"]]
            msp.add_lwpolyline(points, close=bool(entity.get("closed")), dxfattribs={"layer": layer})
        elif entity_type == "LINE":
            start = entity["start"]
            end = entity["end"]
            msp.add_line(
                (start["x"], start["y"]),
                (end["x"], end["y"]),
                dxfattribs={"layer": layer},
            )

    doc.saveas(output_path)


def layout_to_dxf_bytes(layout: GeneratedLayoutDocument) -> bytes:
    """Return DXF file bytes for AutoCAD import."""
    try:
        import io

        import ezdxf
    except ImportError as exc:
        raise RuntimeError("ezdxf is required for DXF export. pip install ezdxf") from exc

    blueprint = export_layout_to_dxf_dict(layout)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    for layer_name, props in blueprint["layers"].items():
        doc.layers.add(layer_name, color=int(props["color"]))

    for entity in blueprint["entities"]:
        entity_type = entity["type"]
        layer = str(entity["layer"])
        if entity_type == "LWPOLYLINE":
            points = [(p["x"], p["y"]) for p in entity["points"]]
            msp.add_lwpolyline(points, close=bool(entity.get("closed")), dxfattribs={"layer": layer})
        elif entity_type == "LINE":
            start = entity["start"]
            end = entity["end"]
            msp.add_line(
                (start["x"], start["y"]),
                (end["x"], end["y"]),
                dxfattribs={"layer": layer},
            )

    stream = io.BytesIO()
    doc.write(stream)
    return stream.getvalue()


def _coords(points: list[Point2D]) -> list[dict[str, float]]:
    return [{"x": point.x, "y": point.y} for point in points]
