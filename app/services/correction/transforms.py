"""Deterministic 2D geometry transforms for layout auto-correction."""

from __future__ import annotations

import math

from app.models.schemas import Point2D
from app.services.geometry import shapely_ops

ZONE_MID_ANGLES: dict[str, float] = {
    "north": 0.0,
    "north_east": 45.0,
    "east": 90.0,
    "south_east": 135.0,
    "south": 180.0,
    "south_west": 225.0,
    "west": 270.0,
    "north_west": 315.0,
}


def translate_polygon(polygon: list[Point2D], dx: float, dy: float) -> list[Point2D]:
    return [Point2D(x=p.x + dx, y=p.y + dy) for p in polygon]


def polygon_centroid(polygon: list[Point2D]) -> Point2D:
    _, centroid = shapely_ops.compute_area_centroid(polygon)
    return centroid


def zone_unit_vector(zone: str) -> tuple[float, float]:
    """Compass unit vector: North=0° → (dx=0, dy=1) in plan coordinates."""
    angle_rad = math.radians(ZONE_MID_ANGLES.get(zone, 0.0))
    return round(math.sin(angle_rad), 6), round(math.cos(angle_rad), 6)


def zone_shift_vector(current_zone: str, target_zone: str) -> tuple[float, float]:
    cx, cy = zone_unit_vector(current_zone)
    tx, ty = zone_unit_vector(target_zone)
    dx, dy = tx - cx, ty - cy
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return 0.0, 0.0
    return round(dx / length, 6), round(dy / length, 6)


def zone_target_point(
    plot_center: Point2D,
    target_zone: str,
    *,
    radius_fraction: float = 0.55,
    plot_radius: float,
) -> Point2D:
    """Point inside plot boundary toward the middle of a Vastu zone wedge."""
    ux, uy = zone_unit_vector(target_zone)
    distance = plot_radius * radius_fraction
    return Point2D(
        x=round(plot_center.x + ux * distance, 4),
        y=round(plot_center.y + uy * distance, 4),
    )


def translation_to_target(
    current_centroid: Point2D,
    target_point: Point2D,
    *,
    max_distance: float | None = None,
) -> tuple[float, float]:
    dx = target_point.x - current_centroid.x
    dy = target_point.y - current_centroid.y
    if max_distance is not None:
        length = math.hypot(dx, dy)
        if length > max_distance and length > 1e-9:
            scale = max_distance / length
            dx *= scale
            dy *= scale
    return round(dx, 4), round(dy, 4)


def rectangle_for_area(
    center: Point2D,
    area: float,
    *,
    aspect_ratio: float = 1.25,
) -> list[Point2D]:
    """Axis-aligned rectangle with given area centered at point."""
    height = math.sqrt(area / aspect_ratio)
    width = area / height if height > 0 else math.sqrt(area)
    half_w = width / 2.0
    half_h = height / 2.0
    return [
        Point2D(x=center.x - half_w, y=center.y - half_h),
        Point2D(x=center.x + half_w, y=center.y - half_h),
        Point2D(x=center.x + half_w, y=center.y + half_h),
        Point2D(x=center.x - half_w, y=center.y + half_h),
    ]


def clip_polygon_to_boundary(
    polygon: list[Point2D],
    boundary: list[Point2D],
) -> list[Point2D]:
    """Intersect room polygon with plot boundary; fall back to original if clip fails."""
    if not shapely_ops.SHAPELY_AVAILABLE or len(boundary) < 3:
        return polygon

    from shapely.geometry import Polygon

    room_shape = shapely_ops.polygon_from_points(polygon)
    bound_shape = shapely_ops.polygon_from_points(boundary)
    if room_shape is None or bound_shape is None:
        return polygon

    clipped = room_shape.intersection(bound_shape)
    if clipped.is_empty:
        return polygon

    if clipped.geom_type == "Polygon":
        coords = list(clipped.exterior.coords)[:-1]
        return [Point2D(x=float(x), y=float(y)) for x, y in coords]

    if clipped.geom_type == "MultiPolygon":
        largest = max(clipped.geoms, key=lambda shape: shape.area)
        coords = list(largest.exterior.coords)[:-1]
        return [Point2D(x=float(x), y=float(y)) for x, y in coords]

    return polygon


def polygon_within_boundary(polygon: list[Point2D], boundary: list[Point2D]) -> bool:
    if not shapely_ops.SHAPELY_AVAILABLE or len(boundary) < 3:
        return True

    room_shape = shapely_ops.polygon_from_points(polygon)
    bound_shape = shapely_ops.polygon_from_points(boundary)
    if room_shape is None or bound_shape is None:
        return True

    if bound_shape.covers(room_shape) or room_shape.within(bound_shape):
        return True

    centroid = room_shape.centroid
    if not bound_shape.contains(centroid):
        return False

    intersection = room_shape.intersection(bound_shape)
    if intersection.is_empty or room_shape.area <= 0:
        return False
    return (intersection.area / room_shape.area) >= 0.95


def ensure_polygon_in_boundary(
    polygon: list[Point2D],
    boundary: list[Point2D],
    plot_center: Point2D,
    *,
    max_iterations: int = 12,
    step_feet: float = 1.0,
) -> list[Point2D]:
    """Clip then nudge toward plot center until polygon fits inside boundary."""
    current = clip_polygon_to_boundary(polygon, boundary)
    if polygon_within_boundary(current, boundary):
        return current

    for _ in range(max_iterations):
        centroid = polygon_centroid(current)
        dx = (plot_center.x - centroid.x) * 0.25
        dy = (plot_center.y - centroid.y) * 0.25
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            break
        length = math.hypot(dx, dy)
        if length > step_feet:
            scale = step_feet / length
            dx *= scale
            dy *= scale
        current = clip_polygon_to_boundary(
            translate_polygon(current, dx, dy),
            boundary,
        )
        if polygon_within_boundary(current, boundary):
            return current

    return current


def compute_plot_boundary(room_polygons: list[list[Point2D]]) -> list[Point2D]:
    """Convex hull of all room polygons, or axis-aligned bounding box fallback."""
    if not room_polygons:
        return []

    if shapely_ops.SHAPELY_AVAILABLE:
        from shapely.geometry import MultiPolygon, Polygon
        from shapely.ops import unary_union

        shapes = [shapely_ops.polygon_from_points(poly) for poly in room_polygons]
        valid = [shape for shape in shapes if shape is not None and not shape.is_empty]
        if valid:
            union = unary_union(valid)
            hull = union.convex_hull if hasattr(union, "convex_hull") else union
            if hull.geom_type == "Polygon":
                coords = list(hull.exterior.coords)[:-1]
                return [Point2D(x=float(x), y=float(y)) for x, y in coords]

    all_points = [point for poly in room_polygons for point in poly]
    min_x = min(p.x for p in all_points)
    max_x = max(p.x for p in all_points)
    min_y = min(p.y for p in all_points)
    max_y = max(p.y for p in all_points)
    return [
        Point2D(x=min_x, y=min_y),
        Point2D(x=max_x, y=min_y),
        Point2D(x=max_x, y=max_y),
        Point2D(x=min_x, y=max_y),
    ]
