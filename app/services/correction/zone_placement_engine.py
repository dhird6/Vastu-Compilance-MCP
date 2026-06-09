"""High-accuracy zone-based room placement with overlap avoidance."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.vastu_zones import VastuZoneCatalog
from app.models.schemas import GeneratedRoomPlacement, Point2D, RoomOrientation
from app.services.correction.transforms import (
    compute_plot_boundary,
    ensure_polygon_in_boundary,
    polygon_centroid,
    rectangle_for_area,
    zone_target_point,
)
from app.services.geometry import shapely_ops


@dataclass(slots=True)
class PlacementSlot:
    room_id: str
    target_zone: str
    radius_fraction: float
    angle_offset_deg: float


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


class ZonePlacementEngine:
    """
    Places room rectangles into Vastu zone wedges inside plot boundary.

    Uses deterministic geometry (Shapely when available) to minimize overlaps.
    """

    def place_rooms(
        self,
        *,
        orientations: list[RoomOrientation],
        target_zones: dict[str, str],
        plot_center: Point2D,
        plot_radius: float,
        plot_boundary: list[Point2D],
        true_north_degrees: float,
        locked_polygons: dict[str, list[Point2D]],
        resolve_zone,
    ) -> list[GeneratedRoomPlacement]:
        placed: list[GeneratedRoomPlacement] = []
        occupied: list[object] = []

        if shapely_ops.SHAPELY_AVAILABLE:
            from shapely.geometry import Polygon

            for polygon in locked_polygons.values():
                shape = shapely_ops.polygon_from_points(polygon)
                if shape is not None:
                    occupied.append(shape)

        slot_index = 0
        for room in orientations:
            if room.room_id in locked_polygons:
                polygon = locked_polygons[room.room_id]
                centroid = polygon_centroid(polygon)
                area, _ = shapely_ops.compute_area_centroid(polygon)
                placed.append(
                    GeneratedRoomPlacement(
                        room_id=room.room_id,
                        room_name=room.room_name,
                        room_type=room.room_type,
                        polygon=polygon,
                        area=area,
                        centroid=centroid,
                        zone=room.zone,
                        source="deterministic",
                    )
                )
                continue

            target_zone = target_zones.get(room.room_id, room.zone)
            slot = _slot_for_index(target_zone, slot_index)
            slot_index += 1

            polygon = self._place_with_collision_avoidance(
                room=room,
                slot=slot,
                plot_center=plot_center,
                plot_radius=plot_radius,
                plot_boundary=plot_boundary,
                occupied=occupied,
            )
            centroid = polygon_centroid(polygon)
            zone = resolve_zone(
                shapely_ops.bearing_from_center(centroid, plot_center, true_north_degrees)
            )
            area, _ = shapely_ops.compute_area_centroid(polygon)

            if shapely_ops.SHAPELY_AVAILABLE:
                from shapely.geometry import Polygon

                shape = shapely_ops.polygon_from_points(polygon)
                if shape is not None:
                    occupied.append(shape)

            placed.append(
                GeneratedRoomPlacement(
                    room_id=room.room_id,
                    room_name=room.room_name,
                    room_type=room.room_type,
                    polygon=polygon,
                    area=area,
                    centroid=centroid,
                    zone=zone,
                    source="deterministic",
                )
            )

        return placed

    def _place_with_collision_avoidance(
        self,
        *,
        room: RoomOrientation,
        slot: PlacementSlot,
        plot_center: Point2D,
        plot_radius: float,
        plot_boundary: list[Point2D],
        occupied: list[object],
    ) -> list[Point2D]:
        base_angle = ZONE_MID_ANGLES.get(slot.target_zone, 0.0) + slot.angle_offset_deg
        for attempt in range(12):
            radius_fraction = max(0.25, min(0.72, slot.radius_fraction + attempt * 0.04))
            angle_rad = math.radians(base_angle + attempt * 11.0)
            ux = math.sin(angle_rad)
            uy = math.cos(angle_rad)
            distance = plot_radius * radius_fraction
            center = Point2D(
                x=plot_center.x + ux * distance,
                y=plot_center.y + uy * distance,
            )
            aspect = 1.2 if room.area < 100 else 1.35
            polygon = rectangle_for_area(center, max(room.area, 1.0), aspect_ratio=aspect)
            polygon = ensure_polygon_in_boundary(polygon, plot_boundary, plot_center)

            if not occupied or not shapely_ops.SHAPELY_AVAILABLE:
                return polygon

            candidate = shapely_ops.polygon_from_points(polygon)
            if candidate is None:
                return polygon

            if all(not candidate.intersects(other.buffer(0.15)) for other in occupied):
                return polygon

        return ensure_polygon_in_boundary(
            rectangle_for_area(
                zone_target_point(plot_center, slot.target_zone, plot_radius=plot_radius),
                max(room.area, 1.0),
            ),
            plot_boundary,
            plot_center,
        )


def resolve_target_zones_from_report(
    orientations: list[RoomOrientation],
    rule_results: list,
) -> dict[str, str]:
    targets: dict[str, str] = {}
    for result in rule_results:
        if result.passed or not result.expected_zones:
            continue
        targets[result.room_id] = result.expected_zones[0]

    for room in orientations:
        if room.room_id in targets:
            continue
        for zone in VastuZoneCatalog.ZONES:
            if room.room_type in zone.recommended_uses:
                targets[room.room_id] = zone.key
                break
        targets.setdefault(room.room_id, room.zone)
    return targets


def _slot_for_index(zone: str, index: int) -> PlacementSlot:
    offsets = [0.0, 12.0, -12.0, 24.0, -24.0]
    radii = [0.52, 0.58, 0.46, 0.64, 0.40]
    offset = offsets[index % len(offsets)]
    radius = radii[index % len(radii)]
    return PlacementSlot(
        room_id="",
        target_zone=zone,
        radius_fraction=radius,
        angle_offset_deg=offset,
    )
