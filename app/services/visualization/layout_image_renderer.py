"""Render 2D floor plans as SVG images (original vs Vastu-corrected)."""

from __future__ import annotations

import base64
from xml.sax.saxutils import escape

from app.models.schemas import (
    ElementType,
    FloorPlanPayload,
    LayoutImageArtifact,
    LayoutImageBundle,
    Point2D,
)


class LayoutImageRenderer:
    """Deterministic SVG renderer for layout comparison images."""

    def render_bundle(
        self,
        original: FloorPlanPayload,
        corrected: FloorPlanPayload | None = None,
        *,
        locked_room_ids: set[str] | None = None,
    ) -> LayoutImageBundle:
        locked = locked_room_ids or set()
        original_svg = self._render_payload(original, title="Original Layout", locked_room_ids=locked)
        bundle = LayoutImageBundle(original=original_svg)

        if corrected is not None:
            bundle.corrected = self._render_payload(
                corrected,
                title="Vastu-Corrected Layout",
                locked_room_ids=locked,
                highlight_changed=True,
                reference=original,
            )
            bundle.comparison = self._render_comparison(original, corrected, locked)

        return bundle

    def _render_payload(
        self,
        payload: FloorPlanPayload,
        *,
        title: str,
        locked_room_ids: set[str],
        highlight_changed: bool = False,
        reference: FloorPlanPayload | None = None,
    ) -> LayoutImageArtifact:
        bounds = _compute_bounds(payload)
        width, height = 900, 650
        scale, offset_x, offset_y = _fit_transform(bounds, width, height, padding=40)

        ref_rooms = {}
        if reference is not None:
            ref_rooms = {
                element.id: element.polygon
                for element in reference.elements
                if element.element_type == ElementType.room
            }

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#1a1f2e"/>',
            f'<text x="20" y="28" fill="#e8ecf4" font-family="Arial" font-size="18">{escape(title)}</text>',
            _north_arrow(width - 60, 50),
        ]

        for element in payload.elements:
            if element.element_type == ElementType.wall:
                parts.append(_polyline(element.polygon, scale, offset_x, offset_y, "#8899aa", 2, False))
            elif element.element_type in {ElementType.door, ElementType.window}:
                parts.append(_polyline(element.polygon, scale, offset_x, offset_y, "#c9a227", 2, False))

        for element in payload.elements:
            if element.element_type != ElementType.room:
                continue
            changed = highlight_changed and _polygon_changed(ref_rooms.get(element.id), element.polygon)
            locked = element.id in locked_room_ids
            if locked:
                fill, stroke = "#4a5568", "#a0aec0"
            elif changed:
                fill, stroke = "#1f6b4a", "#4ade80"
            else:
                fill, stroke = "#234e52", "#2dd4bf"
            parts.append(
                _polygon(element.polygon, scale, offset_x, offset_y, fill, stroke, element.name, locked)
            )

        parts.append("</svg>")
        svg = "\n".join(parts)
        return LayoutImageArtifact(
            format="svg",
            content=svg,
            label=title,
            width=width,
            height=height,
        )

    def _render_comparison(
        self,
        original: FloorPlanPayload,
        corrected: FloorPlanPayload,
        locked_room_ids: set[str],
    ) -> LayoutImageArtifact:
        bounds = _compute_bounds(original)
        width, height = 900, 650
        scale, offset_x, offset_y = _fit_transform(bounds, width, height, padding=40)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#1a1f2e"/>',
            '<text x="20" y="28" fill="#e8ecf4" font-family="Arial" font-size="18">'
            "Before (gray) vs After (green)</text>",
            _north_arrow(width - 60, 50),
        ]

        for element in original.elements:
            if element.element_type == ElementType.room:
                parts.append(
                    _polygon(element.polygon, scale, offset_x, offset_y, "#2d3748", "#718096", "", False, 0.35)
                )

        for element in corrected.elements:
            if element.element_type != ElementType.room:
                continue
            locked = element.id in locked_room_ids
            parts.append(
                _polygon(
                    element.polygon,
                    scale,
                    offset_x,
                    offset_y,
                    "none",
                    "#4ade80" if not locked else "#a0aec0",
                    element.name if not locked else f"{element.name} (fixed)",
                    locked,
                    0.9,
                )
            )

        parts.append("</svg>")
        return LayoutImageArtifact(format="svg", content="\n".join(parts), label="comparison", width=width, height=height)


def svg_to_base64(artifact: LayoutImageArtifact) -> str:
    return base64.b64encode(artifact.content.encode("utf-8")).decode("ascii")


def _compute_bounds(payload: FloorPlanPayload) -> tuple[float, float, float, float]:
    points = [point for element in payload.elements for point in element.polygon]
    if not points:
        return 0.0, 0.0, 10.0, 10.0
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _fit_transform(
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    *,
    padding: float,
) -> tuple[float, float, float]:
    min_x, min_y, max_x, max_y = bounds
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((width - 2 * padding) / span_x, (height - 2 * padding) / span_y)
    offset_x = padding - min_x * scale
    offset_y = height - padding + min_y * scale
    return scale, offset_x, offset_y


def _transform(point: Point2D, scale: float, offset_x: float, offset_y: float) -> tuple[float, float]:
    return point.x * scale + offset_x, offset_y - point.y * scale


def _polygon(
    polygon: list[Point2D],
    scale: float,
    offset_x: float,
    offset_y: float,
    fill: str,
    stroke: str,
    label: str,
    locked: bool,
    opacity: float = 0.75,
) -> str:
    if len(polygon) < 3:
        return ""
    coords = " ".join(
        f"{_transform(point, scale, offset_x, offset_y)[0]:.1f},{_transform(point, scale, offset_x, offset_y)[1]:.1f}"
        for point in polygon
    )
    cx = sum(_transform(point, scale, offset_x, offset_y)[0] for point in polygon) / len(polygon)
    cy = sum(_transform(point, scale, offset_x, offset_y)[1] for point in polygon) / len(polygon)
    label_svg = ""
    if label:
        suffix = " 🔒" if locked else ""
        label_svg = (
            f'<text x="{cx:.1f}" y="{cy:.1f}" fill="#ffffff" font-size="11" '
            f'text-anchor="middle" font-family="Arial">{escape(label + suffix)}</text>'
        )
    return (
        f'<polygon points="{coords}" fill="{fill}" fill-opacity="{opacity}" '
        f'stroke="{stroke}" stroke-width="2"/>{label_svg}'
    )


def _polyline(
    polygon: list[Point2D],
    scale: float,
    offset_x: float,
    offset_y: float,
    stroke: str,
    width: int,
    closed: bool,
) -> str:
    if len(polygon) < 2:
        return ""
    coords = " ".join(
        f"{_transform(point, scale, offset_x, offset_y)[0]:.1f},{_transform(point, scale, offset_x, offset_y)[1]:.1f}"
        for point in polygon
    )
    return f'<polyline points="{coords}" fill="none" stroke="{stroke}" stroke-width="{width}"/>'


def _north_arrow(x: float, y: float) -> str:
    return (
        f'<g transform="translate({x},{y})">'
        f'<line x1="0" y1="20" x2="0" y2="-20" stroke="#60a5fa" stroke-width="2"/>'
        f'<polygon points="0,-28 -6,-16 6,-16" fill="#60a5fa"/>'
        f'<text x="0" y="36" fill="#60a5fa" font-size="11" text-anchor="middle">N</text>'
        f"</g>"
    )


def _polygon_changed(original: list[Point2D] | None, corrected: list[Point2D]) -> bool:
    if original is None or len(original) != len(corrected):
        return True
    for point_a, point_b in zip(original, corrected):
        if abs(point_a.x - point_b.x) > 0.05 or abs(point_a.y - point_b.y) > 0.05:
            return True
    return False
