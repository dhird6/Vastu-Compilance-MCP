"""Server-side DXF/DWG parsing via ezdxf."""

from __future__ import annotations

from pathlib import Path

from app.models.schemas import (
    AutocadEntity2D,
    AutocadEntityType,
    AutocadLayoutPayload,
    Point2D,
)


def parse_dxf_layout(
    file_path: Path,
    *,
    layout_name: str = "Model",
    true_north_degrees: float = 0.0,
    layer_filter: str | None = None,
) -> AutocadLayoutPayload:
    """
    Parse closed polylines on room layers into AutocadLayoutPayload.

    Requires ezdxf. Layer naming convention: ROOM_* or explicit layer_filter.
    """
    try:
        import ezdxf
    except ImportError as exc:
        raise RuntimeError("ezdxf is required for DXF parsing. pip install ezdxf") from exc

    doc = ezdxf.readfile(str(file_path))
    msp = doc.modelspace()
    entities: list[AutocadEntity2D] = []

    for index, entity in enumerate(msp.query("LWPOLYLINE")):
        layer = entity.dxf.layer
        if layer_filter and layer != layer_filter:
            continue
        if not layer.upper().startswith("ROOM") and layer_filter is None:
            continue
        points = [Point2D(x=float(x), y=float(y)) for x, y, *_ in entity.get_points()]
        if len(points) < 3 or not entity.closed:
            continue
        room_type = layer.replace("ROOM_", "").replace("ROOM-", "").lower() or "room"
        entities.append(
            AutocadEntity2D(
                id=f"dxf-{index}",
                name=layer,
                entity_type=AutocadEntityType.room,
                points=points,
                metadata={"room_type": room_type, "source": "ezdxf"},
            )
        )

    return AutocadLayoutPayload(
        true_north_degrees=true_north_degrees,
        layout_name=layout_name,
        entities=entities,
    )
