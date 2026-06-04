from __future__ import annotations

from dataclasses import dataclass

from app.domain.vastu_zones import VastuZoneCatalog
from app.models.schemas import (
    AutocadEntityType,
    AutocadLayoutPayload,
    ElementType,
    FloorPlanElement,
    FloorPlanPayload,
    Point2D,
    RevitElement3D,
    RevitElementType,
    RevitModelPayload,
    RoomOrientation,
)
from app.services.geometry import shapely_ops


@dataclass(slots=True)
class PolygonMetrics:
    area: float
    centroid: Point2D
    primary_axis_degrees: float
    zone_bearing_degrees: float
    in_brahmasthan: bool
    adjacent_room_ids: list[str]


class GeometryEngine:
    async def extract_structured_elements(self, payload: FloorPlanPayload) -> FloorPlanPayload:
        return payload

    async def project_revit_3d_to_floorplan(self, payload: RevitModelPayload) -> FloorPlanPayload:
        projected_elements: list[FloorPlanElement] = []
        element_map = {
            RevitElementType.room: ElementType.room,
            RevitElementType.wall: ElementType.wall,
            RevitElementType.door: ElementType.door,
            RevitElementType.window: ElementType.window,
        }
        for element in payload.elements:
            footprint = _footprint_from_element(element)
            projected_elements.append(
                FloorPlanElement(
                    id=element.id,
                    name=element.name,
                    element_type=element_map[element.element_type],
                    polygon=footprint,
                    metadata={
                        **element.metadata,
                        "source_3d_bbox_height": max(
                            0.0,
                            element.bounding_box.max.z - element.bounding_box.min.z,
                        ),
                        "projection_mode": element.metadata.get("projection_mode", "xy_footprint"),
                    },
                )
            )

        return FloorPlanPayload(
            source="revit_3d_projection",
            true_north_degrees=payload.true_north_degrees,
            levels=payload.levels,
            elements=projected_elements,
            model_reference=payload.model_reference,
        )

    async def project_autocad_layout_to_floorplan(self, payload: AutocadLayoutPayload) -> FloorPlanPayload:
        projected_elements: list[FloorPlanElement] = []
        entity_map = {
            AutocadEntityType.room: ElementType.room,
            AutocadEntityType.wall: ElementType.wall,
            AutocadEntityType.door: ElementType.door,
            AutocadEntityType.window: ElementType.window,
        }
        for entity in payload.entities:
            points = entity.points
            if len(points) < 3 and entity.entity_type == AutocadEntityType.room:
                continue
            projected_elements.append(
                FloorPlanElement(
                    id=entity.id,
                    name=entity.name,
                    element_type=entity_map[entity.entity_type],
                    polygon=points,
                    metadata={
                        **entity.metadata,
                        "layout_name": payload.layout_name,
                        "source_entity_type": entity.entity_type.value,
                    },
                )
            )

        return FloorPlanPayload(
            source="direct_json",
            true_north_degrees=payload.true_north_degrees,
            levels=payload.levels,
            elements=projected_elements,
            model_reference=payload.model_reference,
        )

    def calculate_polygon_metrics(
        self,
        polygon: list[Point2D],
        *,
        plot_center: Point2D | None = None,
        plot_radius: float = 0.0,
        true_north_degrees: float = 0.0,
        other_polygons: dict[str, list[Point2D]] | None = None,
    ) -> PolygonMetrics:
        area, centroid = shapely_ops.compute_area_centroid(polygon)
        axis = shapely_ops.primary_axis_degrees(polygon)

        if plot_center is not None:
            zone_bearing = shapely_ops.bearing_from_center(centroid, plot_center, true_north_degrees)
            in_brahmasthan = shapely_ops.is_in_brahmasthan(centroid, plot_center, plot_radius)
        else:
            zone_bearing = (axis + true_north_degrees) % 360.0
            in_brahmasthan = False

        neighbors: list[str] = []
        if other_polygons:
            neighbors = shapely_ops.adjacent_room_ids(polygon, other_polygons)

        return PolygonMetrics(
            area=area,
            centroid=centroid,
            primary_axis_degrees=axis,
            zone_bearing_degrees=zone_bearing,
            in_brahmasthan=in_brahmasthan,
            adjacent_room_ids=neighbors,
        )

    def identify_rooms(self, payload: FloorPlanPayload) -> list:
        return [e for e in payload.elements if e.element_type == ElementType.room]

    def identify_walls(self, payload: FloorPlanPayload) -> list:
        return [e for e in payload.elements if e.element_type == ElementType.wall]

    def identify_doors(self, payload: FloorPlanPayload) -> list:
        return [e for e in payload.elements if e.element_type == ElementType.door]

    def identify_windows(self, payload: FloorPlanPayload) -> list:
        return [e for e in payload.elements if e.element_type == ElementType.window]

    def build_room_orientations(
        self,
        payload: FloorPlanPayload,
        zone_resolver,
    ) -> list[RoomOrientation]:
        rooms = self.identify_rooms(payload)
        room_polygons = [room.polygon for room in rooms]
        plot_center = shapely_ops.compute_plot_center(room_polygons)
        plot_radius = shapely_ops.compute_plot_radius(room_polygons, plot_center)
        polygon_map = {room.id: room.polygon for room in rooms}

        orientations: list[RoomOrientation] = []
        for room in rooms:
            others = {rid: poly for rid, poly in polygon_map.items() if rid != room.id}
            metrics = self.calculate_polygon_metrics(
                room.polygon,
                plot_center=plot_center,
                plot_radius=plot_radius,
                true_north_degrees=payload.true_north_degrees,
                other_polygons=others,
            )
            zone = zone_resolver(metrics.zone_bearing_degrees)
            room_type = str(room.metadata.get("room_type", room.name)).lower()
            orientations.append(
                RoomOrientation(
                    room_id=room.id,
                    room_name=room.name,
                    room_type=room_type,
                    area=metrics.area,
                    centroid=metrics.centroid,
                    orientation_degrees=metrics.zone_bearing_degrees,
                    zone=zone,
                    confidence=0.92 if not metrics.in_brahmasthan else 0.78,
                    metadata={
                        "primary_axis_degrees": metrics.primary_axis_degrees,
                        "in_brahmasthan": metrics.in_brahmasthan,
                        "adjacent_room_ids": metrics.adjacent_room_ids,
                        "plot_center": {"x": plot_center.x, "y": plot_center.y},
                    },
                )
            )
        return orientations

    def evaluate_single_room(
        self,
        *,
        element_id: str,
        room_name: str,
        room_type: str,
        polygon: list[Point2D],
        true_north_degrees: float = 0.0,
        all_room_polygons: dict[str, list[Point2D]] | None = None,
    ) -> RoomOrientation:
        """Stateless single-room evaluation for thin MCP tools."""
        polygons = list((all_room_polygons or {}).values()) + [polygon]
        plot_center = shapely_ops.compute_plot_center(polygons)
        plot_radius = shapely_ops.compute_plot_radius(polygons, plot_center)
        others = {rid: poly for rid, poly in (all_room_polygons or {}).items() if rid != element_id}
        metrics = self.calculate_polygon_metrics(
            polygon,
            plot_center=plot_center,
            plot_radius=plot_radius,
            true_north_degrees=true_north_degrees,
            other_polygons=others,
        )
        zone = VastuZoneCatalog.resolve(metrics.zone_bearing_degrees)
        return RoomOrientation(
            room_id=element_id,
            room_name=room_name,
            room_type=room_type.lower(),
            area=metrics.area,
            centroid=metrics.centroid,
            orientation_degrees=metrics.zone_bearing_degrees,
            zone=zone,
            confidence=0.92 if not metrics.in_brahmasthan else 0.78,
            metadata={
                "primary_axis_degrees": metrics.primary_axis_degrees,
                "in_brahmasthan": metrics.in_brahmasthan,
                "adjacent_room_ids": metrics.adjacent_room_ids,
            },
        )


def _footprint_from_element(element: RevitElement3D) -> list[Point2D]:
    raw = element.metadata.get("footprint_polygon")
    if isinstance(raw, list) and len(raw) >= 3:
        points: list[Point2D] = []
        for item in raw:
            if isinstance(item, dict) and "x" in item and "y" in item:
                points.append(Point2D(x=float(item["x"]), y=float(item["y"])))
        if len(points) >= 3:
            return points

    bbox = element.bounding_box
    return [
        Point2D(x=bbox.min.x, y=bbox.min.y),
        Point2D(x=bbox.max.x, y=bbox.min.y),
        Point2D(x=bbox.max.x, y=bbox.max.y),
        Point2D(x=bbox.min.x, y=bbox.max.y),
    ]
