"""Shapely-backed polygon operations (geometry-first layer)."""

from __future__ import annotations

from math import atan2, degrees

from app.models.schemas import Point2D

try:
    from shapely.geometry import MultiPolygon, Point, Polygon
    from shapely.ops import unary_union

    SHAPELY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when shapely missing
    SHAPELY_AVAILABLE = False
    MultiPolygon = None  # type: ignore[misc, assignment]
    Point = None  # type: ignore[misc, assignment]
    Polygon = None  # type: ignore[misc, assignment]
    unary_union = None  # type: ignore[misc, assignment]


def points_to_coords(polygon: list[Point2D]) -> list[tuple[float, float]]:
    return [(p.x, p.y) for p in polygon]


def polygon_from_points(polygon: list[Point2D]) -> "Polygon | None":
    if not SHAPELY_AVAILABLE or len(polygon) < 3:
        return None
    shape = Polygon(points_to_coords(polygon))
    if not shape.is_valid:
        shape = shape.buffer(0)
    return shape if not shape.is_empty else None


def compute_area_centroid(polygon: list[Point2D]) -> tuple[float, Point2D]:
    shape = polygon_from_points(polygon)
    if shape is None:
        return _shoelace_area_centroid(polygon)
    centroid = shape.centroid
    return float(shape.area), Point2D(x=centroid.x, y=centroid.y)


def compute_plot_center(room_polygons: list[list[Point2D]]) -> Point2D:
    if not room_polygons:
        return Point2D(x=0.0, y=0.0)

    if SHAPELY_AVAILABLE:
        shapes = [polygon_from_points(poly) for poly in room_polygons]
        valid = [s for s in shapes if s is not None and not s.is_empty]
        if valid:
            union = unary_union(valid)
            center = union.centroid
            return Point2D(x=center.x, y=center.y)

    all_points = [p for poly in room_polygons for p in poly]
    if not all_points:
        return Point2D(x=0.0, y=0.0)
    cx = sum(p.x for p in all_points) / len(all_points)
    cy = sum(p.y for p in all_points) / len(all_points)
    return Point2D(x=cx, y=cy)


def bearing_from_center(
    centroid: Point2D,
    plot_center: Point2D,
    true_north_degrees: float,
) -> float:
    """
    Compass bearing from plot center to room centroid.

    North = 0°, East = 90°, South = 180°, West = 270° (True North adjusted).
    """
    dx = centroid.x - plot_center.x
    dy = centroid.y - plot_center.y
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return true_north_degrees % 360.0
    # atan2(dy, dx): 0°=East, 90°=North → compass = (90 - angle) % 360
    compass = (90.0 - degrees(atan2(dy, dx))) % 360.0
    return (compass + true_north_degrees) % 360.0


def is_in_brahmasthan(
    centroid: Point2D,
    plot_center: Point2D,
    plot_radius: float,
    brahmasthan_fraction: float = 0.15,
) -> bool:
    """Room centroid within inner fraction of plot radius = Brahmasthan overlap."""
    if plot_radius <= 0:
        return False
    dx = centroid.x - plot_center.x
    dy = centroid.y - plot_center.y
    distance = (dx * dx + dy * dy) ** 0.5
    return distance <= plot_radius * brahmasthan_fraction


def compute_plot_radius(room_polygons: list[list[Point2D]], plot_center: Point2D) -> float:
    if SHAPELY_AVAILABLE:
        shapes = [polygon_from_points(poly) for poly in room_polygons]
        valid = [s for s in shapes if s is not None and not s.is_empty]
        if valid:
            union = unary_union(valid)
            bounds = union.bounds  # minx, miny, maxx, maxy
            corners = [
                Point2D(x=bounds[0], y=bounds[1]),
                Point2D(x=bounds[2], y=bounds[1]),
                Point2D(x=bounds[2], y=bounds[3]),
                Point2D(x=bounds[0], y=bounds[3]),
            ]
            return max(
                ((c.x - plot_center.x) ** 2 + (c.y - plot_center.y) ** 2) ** 0.5
                for c in corners
            )

    max_dist = 0.0
    for poly in room_polygons:
        for p in poly:
            dist = ((p.x - plot_center.x) ** 2 + (p.y - plot_center.y) ** 2) ** 0.5
            max_dist = max(max_dist, dist)
    return max_dist


def adjacent_room_ids(room_polygon: list[Point2D], others: dict[str, list[Point2D]]) -> list[str]:
    if not SHAPELY_AVAILABLE:
        return []
    base = polygon_from_points(room_polygon)
    if base is None:
        return []
    neighbors: list[str] = []
    for room_id, poly in others.items():
        other = polygon_from_points(poly)
        if other is None:
            continue
        if base.touches(other) or base.intersects(other.buffer(0.01)):
            neighbors.append(room_id)
    return neighbors


def primary_axis_degrees(polygon: list[Point2D]) -> float:
    if len(polygon) < 2:
        return 0.0
    longest_length_sq = -1.0
    dx = dy = 0.0
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        edge_dx = polygon[j].x - polygon[i].x
        edge_dy = polygon[j].y - polygon[i].y
        length_sq = edge_dx * edge_dx + edge_dy * edge_dy
        if length_sq > longest_length_sq:
            longest_length_sq = length_sq
            dx, dy = edge_dx, edge_dy
    return (degrees(atan2(dy, dx)) + 360.0) % 360.0


def _shoelace_area_centroid(polygon: list[Point2D]) -> tuple[float, Point2D]:
    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        cross = polygon[i].x * polygon[j].y - polygon[j].x * polygon[i].y
        signed_area += cross
        cx += (polygon[i].x + polygon[j].x) * cross
        cy += (polygon[i].y + polygon[j].y) * cross
    signed_area *= 0.5
    area = abs(signed_area)
    if signed_area == 0:
        return area, Point2D(x=polygon[0].x, y=polygon[0].y)
    cx /= 6.0 * signed_area
    cy /= 6.0 * signed_area
    return area, Point2D(x=cx, y=cy)
