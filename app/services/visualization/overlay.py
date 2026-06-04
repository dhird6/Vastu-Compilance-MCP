from __future__ import annotations

from app.models.schemas import HeatmapCell, RoomOrientation, RuleEvaluationResult


class VisualizationEngine:
    def build_heatmap(
        self,
        room_orientations: list[RoomOrientation],
        rule_results: list[RuleEvaluationResult],
    ) -> list[HeatmapCell]:
        by_room = {result.room_id: result for result in rule_results}
        cells: list[HeatmapCell] = []

        for room in room_orientations:
            result = by_room.get(room.room_id)
            if not result:
                cells.append(
                    HeatmapCell(
                        room_id=room.room_id,
                        zone=room.zone,
                        score=0.8,
                        color_hex="#9ACD32",
                        status="compliant",
                    )
                )
                continue

            if result.passed:
                cells.append(
                    HeatmapCell(
                        room_id=room.room_id,
                        zone=room.zone,
                        score=0.9,
                        color_hex="#2E8B57",
                        status="compliant",
                    )
                )
            else:
                critical = result.severity.value in {"critical", "high"}
                cells.append(
                    HeatmapCell(
                        room_id=room.room_id,
                        zone=room.zone,
                        score=0.35 if critical else 0.55,
                        color_hex="#DC143C" if critical else "#FF8C00",
                        status="critical" if critical else "warning",
                    )
                )
        return cells

    def build_overlay_payload(
        self,
        room_orientations: list[RoomOrientation],
        directional_zones: list[dict[str, float | str]],
    ) -> dict:
        return {
            "zones": directional_zones,
            "room_vectors": [
                {
                    "room_id": room.room_id,
                    "centroid": room.centroid.model_dump(),
                    "orientation_degrees": room.orientation_degrees,
                    "zone": room.zone,
                }
                for room in room_orientations
            ],
        }
