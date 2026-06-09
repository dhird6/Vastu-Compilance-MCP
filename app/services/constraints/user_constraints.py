"""User constraints — preserve rooms/zones the owner wants unchanged."""

from __future__ import annotations

import math

from app.models.schemas import (
    ConstraintValidationResult,
    CorrectedLayoutResult,
    FloorPlanElement,
    FloorPlanPayload,
    GhostRoomCorrection,
    Point2D,
    RoomOrientation,
    RuleEvaluationResult,
    UserConstraintKind,
    UserLayoutConstraint,
)
from app.services.correction.transforms import polygon_centroid
from app.services.geometry import shapely_ops


class UserConstraintEngine:
    def resolve_locked_room_ids(
        self,
        constraints: list[UserLayoutConstraint],
        payload: FloorPlanPayload,
    ) -> set[str]:
        locked: set[str] = set()
        room_elements = {
            element.id: element
            for element in payload.elements
            if element.element_type.value == "room"
        }
        room_type_index: dict[str, list[str]] = {}
        for element in room_elements.values():
            room_type = str(element.metadata.get("room_type", element.name)).lower()
            room_type_index.setdefault(room_type, []).append(element.id)

        for constraint in constraints:
            if constraint.kind == UserConstraintKind.fixed_room and constraint.room_id:
                locked.add(constraint.room_id)
            elif constraint.kind == UserConstraintKind.fixed_zone and constraint.room_id:
                locked.add(constraint.room_id)
            elif constraint.kind == UserConstraintKind.preserve_room_type and constraint.room_type:
                for room_id in room_type_index.get(constraint.room_type.lower(), []):
                    locked.add(room_id)

        return locked

    def filter_correctable_failures(
        self,
        failures: list[RuleEvaluationResult],
        locked_room_ids: set[str],
    ) -> tuple[list[RuleEvaluationResult], list[str]]:
        allowed: list[RuleEvaluationResult] = []
        skipped: list[str] = []
        for failure in failures:
            if failure.room_id in locked_room_ids:
                skipped.append(failure.room_id)
                continue
            allowed.append(failure)
        return allowed, skipped

    def validate_correction(
        self,
        *,
        original: FloorPlanPayload,
        corrected: CorrectedLayoutResult,
        constraints: list[UserLayoutConstraint],
        orientations: list[RoomOrientation],
    ) -> ConstraintValidationResult:
        locked = self.resolve_locked_room_ids(constraints, original)
        violations: list[dict[str, str]] = []
        satisfied: list[str] = []

        original_rooms = {
            element.id: element
            for element in original.elements
            if element.element_type.value == "room"
        }
        corrected_rooms = {
            element.id: element
            for element in corrected.corrected_payload.elements
            if element.element_type.value == "room"
        }
        orientation_map = {room.room_id: room for room in orientations}

        for constraint in constraints:
            if constraint.kind == UserConstraintKind.fixed_room and constraint.room_id:
                if self._room_moved(original_rooms, corrected_rooms, constraint.room_id):
                    violations.append(
                        {
                            "constraint_id": constraint.constraint_id,
                            "code": "FIXED_ROOM_MOVED",
                            "message": f"Room '{constraint.room_id}' was moved but marked fixed.",
                        }
                    )
                else:
                    satisfied.append(constraint.constraint_id)

            elif constraint.kind == UserConstraintKind.fixed_zone and constraint.room_id and constraint.zone:
                corrected_room = corrected_rooms.get(constraint.room_id)
                if corrected_room is None:
                    continue
                centroid = polygon_centroid(corrected_room.polygon)
                plot_center = shapely_ops.compute_plot_center(
                    [element.polygon for element in original_rooms.values()]
                )
                bearing = shapely_ops.bearing_from_center(
                    centroid, plot_center, original.true_north_degrees
                )
                from app.domain.vastu_zones import VastuZoneCatalog

                zone = VastuZoneCatalog.resolve(bearing)
                if zone != constraint.zone:
                    violations.append(
                        {
                            "constraint_id": constraint.constraint_id,
                            "code": "FIXED_ZONE_VIOLATED",
                            "message": (
                                f"Room '{constraint.room_id}' is in '{zone}' "
                                f"but must stay in '{constraint.zone}'."
                            ),
                        }
                    )
                else:
                    satisfied.append(constraint.constraint_id)

            elif constraint.kind == UserConstraintKind.max_move and constraint.room_id:
                max_feet = constraint.max_translation_feet or 1.0
                distance = self._movement_distance(
                    original_rooms.get(constraint.room_id),
                    corrected_rooms.get(constraint.room_id),
                )
                if distance > max_feet + 0.01:
                    violations.append(
                        {
                            "constraint_id": constraint.constraint_id,
                            "code": "MAX_MOVE_EXCEEDED",
                            "message": (
                                f"Room '{constraint.room_id}' moved {distance:.2f} ft "
                                f"(max {max_feet:.2f} ft)."
                            ),
                        }
                    )
                else:
                    satisfied.append(constraint.constraint_id)

            elif constraint.kind == UserConstraintKind.preserve_room_type and constraint.room_type:
                for room in orientation_map.values():
                    if room.room_type == constraint.room_type.lower():
                        satisfied.append(constraint.constraint_id)

        for room_id in locked:
            if self._room_moved(original_rooms, corrected_rooms, room_id):
                violations.append(
                    {
                        "constraint_id": f"locked-{room_id}",
                        "code": "LOCKED_ROOM_MOVED",
                        "message": f"Locked room '{room_id}' was modified.",
                    }
                )
            else:
                satisfied.append(f"locked-{room_id}")

        return ConstraintValidationResult(
            valid=len(violations) == 0,
            locked_room_ids=sorted(locked),
            skipped_corrections=[],
            violations=violations,
            satisfied_constraints=satisfied,
        )

    def validate_ghost_corrections(
        self,
        corrections: list[GhostRoomCorrection],
        constraints: list[UserLayoutConstraint],
        original: FloorPlanPayload,
    ) -> ConstraintValidationResult:
        locked = self.resolve_locked_room_ids(constraints, original)
        violations: list[dict[str, str]] = []
        skipped: list[str] = []

        for correction in corrections:
            if correction.room_id in locked:
                violations.append(
                    {
                        "constraint_id": correction.room_id,
                        "code": "CORRECTION_ON_LOCKED_ROOM",
                        "message": f"Attempted correction on locked room '{correction.room_id}'.",
                    }
                )

        for constraint in constraints:
            if constraint.kind != UserConstraintKind.max_move or not constraint.room_id:
                continue
            correction = next(
                (item for item in corrections if item.room_id == constraint.room_id),
                None,
            )
            if correction is None:
                continue
            translation = correction.translation
            distance = math.hypot(translation.get("x", 0.0), translation.get("y", 0.0))
            max_feet = constraint.max_translation_feet or 1.0
            if distance > max_feet + 0.01:
                violations.append(
                    {
                        "constraint_id": constraint.constraint_id,
                        "code": "MAX_MOVE_EXCEEDED",
                        "message": (
                            f"Proposed move for '{constraint.room_id}' is {distance:.2f} ft "
                            f"(max {max_feet:.2f} ft)."
                        ),
                    }
                )

        return ConstraintValidationResult(
            valid=len(violations) == 0,
            locked_room_ids=sorted(locked),
            skipped_corrections=skipped,
            violations=violations,
            satisfied_constraints=[],
        )

    @staticmethod
    def _room_moved(
        original_rooms: dict[str, FloorPlanElement],
        corrected_rooms: dict[str, FloorPlanElement],
        room_id: str,
    ) -> bool:
        original = original_rooms.get(room_id)
        corrected = corrected_rooms.get(room_id)
        if original is None or corrected is None:
            return False
        if len(original.polygon) != len(corrected.polygon):
            return True
        for point_a, point_b in zip(original.polygon, corrected.polygon):
            if abs(point_a.x - point_b.x) > 0.05 or abs(point_a.y - point_b.y) > 0.05:
                return True
        return False

    @staticmethod
    def _movement_distance(
        original: FloorPlanElement | None,
        corrected: FloorPlanElement | None,
    ) -> float:
        if original is None or corrected is None:
            return 0.0
        origin_centroid = polygon_centroid(original.polygon)
        corrected_centroid = polygon_centroid(corrected.polygon)
        return math.hypot(
            corrected_centroid.x - origin_centroid.x,
            corrected_centroid.y - origin_centroid.y,
        )
