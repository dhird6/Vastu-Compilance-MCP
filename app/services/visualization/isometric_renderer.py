"""Isometric 3D-style floor plan views for report comparison (deterministic SVG)."""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

from app.models.schemas import ElementType, FloorPlanPayload, LayoutImageArtifact, Point2D


class IsometricLayoutRenderer:
    """Render extruded room volumes in isometric projection for before/after comparison."""

    WALL_HEIGHT_FT = 8.0

    def render_comparison(
        self,
        original: FloorPlanPayload,
        corrected: FloorPlanPayload | None = None,
    ) -> tuple[LayoutImageArtifact, LayoutImageArtifact | None]:
        original_art = self._render_payload(original, title="3D View — Original Layout")
        corrected_art = None
        if corrected is not None:
            corrected_art = self._render_payload(corrected, title="3D View — Vastu-Corrected Layout")
        return original_art, corrected_art

    def _render_payload(self, payload: FloorPlanPayload, *, title: str) -> LayoutImageArtifact:
        width, height = 920, 520
        bounds = _bounds(payload)
        scale, origin_x, origin_y = _fit_isometric(bounds, width, height, padding=80)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<defs>',
            '<linearGradient id="floorGrad" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#2dd4bf" stop-opacity="0.35"/>'
            '<stop offset="100%" stop-color="#0f766e" stop-opacity="0.15"/>'
            '</linearGradient>',
            '<linearGradient id="wallGrad" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0%" stop-color="#334155"/>'
            '<stop offset="100%" stop-color="#1e293b"/>'
            '</linearGradient>',
            "</defs>",
            '<rect width="100%" height="100%" fill="#0f1419"/>',
            f'<text x="24" y="32" fill="#e2e8f0" font-family="Segoe UI, Arial" font-size="18" '
            f'font-weight="600">{escape(title)}</text>',
            _ground_grid(origin_x, origin_y, scale),
        ]

        rooms = [element for element in payload.elements if element.element_type == ElementType.room]
        for room in sorted(rooms, key=lambda item: _polygon_area(item.polygon)):
            parts.extend(_extrude_room(room.polygon, room.name, scale, origin_x, origin_y, self.WALL_HEIGHT_FT))

        parts.append("</svg>")
        svg = "\n".join(parts)
        return LayoutImageArtifact(format="svg", content=svg, label=title, width=width, height=height)


def _project_iso(x: float, y: float, z: float, scale: float, ox: float, oy: float) -> tuple[float, float]:
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    sx = (x - y) * cos30 * scale + ox
    sy = (x + y) * sin30 * scale - z * scale * 0.55 + oy
    return sx, sy


def _bounds(payload: FloorPlanPayload) -> tuple[float, float, float, float]:
    points = [point for element in payload.elements for point in element.polygon]
    if not points:
        return 0.0, 0.0, 12.0, 12.0
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _fit_isometric(
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    *,
    padding: float,
) -> tuple[float, float, float]:
    min_x, min_y, max_x, max_y = bounds
    span = max(max_x - min_x, max_y - min_y, 1.0)
    scale = min((width - 2 * padding) / (span * 1.8), (height - 2 * padding) / (span * 1.4))
    origin_x = width / 2
    origin_y = height - padding
    return scale, origin_x, origin_y


def _polygon_area(polygon: list[Point2D]) -> float:
    if len(polygon) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(polygon):
        nxt = polygon[(index + 1) % len(polygon)]
        area += point.x * nxt.y - nxt.x * point.y
    return abs(area) / 2.0


def _extrude_room(
    polygon: list[Point2D],
    label: str,
    scale: float,
    ox: float,
    oy: float,
    wall_height: float,
) -> list[str]:
    if len(polygon) < 3:
        return []

    parts: list[str] = []
    floor_pts = " ".join(
        f"{_project_iso(p.x, p.y, 0, scale, ox, oy)[0]:.1f},{_project_iso(p.x, p.y, 0, scale, ox, oy)[1]:.1f}"
        for p in polygon
    )
    parts.append(f'<polygon points="{floor_pts}" fill="url(#floorGrad)" stroke="#2dd4bf" stroke-width="1.5"/>')

    for index in range(len(polygon)):
        p0 = polygon[index]
        p1 = polygon[(index + 1) % len(polygon)]
        base0 = _project_iso(p0.x, p0.y, 0, scale, ox, oy)
        base1 = _project_iso(p1.x, p1.y, 0, scale, ox, oy)
        top0 = _project_iso(p0.x, p0.y, wall_height, scale, ox, oy)
        top1 = _project_iso(p1.x, p1.y, wall_height, scale, ox, oy)
        wall = (
            f'<polygon points="{base0[0]:.1f},{base0[1]:.1f} {base1[0]:.1f},{base1[1]:.1f} '
            f'{top1[0]:.1f},{top1[1]:.1f} {top0[0]:.1f},{top0[1]:.1f}" '
            f'fill="url(#wallGrad)" stroke="#475569" stroke-width="0.8" opacity="0.92"/>'
        )
        parts.append(wall)

    cx = sum(point.x for point in polygon) / len(polygon)
    cy = sum(point.y for point in polygon) / len(polygon)
    label_pt = _project_iso(cx, cy, wall_height + 1.5, scale, ox, oy)
    parts.append(
        f'<text x="{label_pt[0]:.1f}" y="{label_pt[1]:.1f}" fill="#f8fafc" font-size="10" '
        f'text-anchor="middle" font-family="Segoe UI, Arial">{escape(label)}</text>'
    )
    return parts


def _ground_grid(ox: float, oy: float, scale: float) -> str:
    lines: list[str] = []
    for offset in range(-6, 7):
        a = _project_iso(offset * 2, -12, 0, scale, ox, oy)
        b = _project_iso(offset * 2, 12, 0, scale, ox, oy)
        lines.append(
            f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
            f'stroke="#1e293b" stroke-width="0.5"/>'
        )
    return "\n".join(lines)
