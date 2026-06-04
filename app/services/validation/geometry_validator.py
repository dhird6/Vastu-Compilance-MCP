from __future__ import annotations

from app.models.schemas import FloorPlanPayload, GeometryValidationIssue, Severity


class GeometryValidator:
    def validate(self, payload: FloorPlanPayload) -> list[GeometryValidationIssue]:
        issues: list[GeometryValidationIssue] = []

        if not payload.elements:
            issues.append(
                GeometryValidationIssue(
                    code="EMPTY_MODEL",
                    message="No elements were provided in the floor plan payload.",
                    severity=Severity.critical,
                    element_id=None,
                )
            )
            return issues

        for element in payload.elements:
            if element.element_type.value == "room" and len(element.polygon) < 3:
                issues.append(
                    GeometryValidationIssue(
                        code="INVALID_ROOM_POLYGON",
                        message="Room polygon has fewer than 3 points.",
                        severity=Severity.high,
                        element_id=element.id,
                    )
                )

            if len(element.polygon) >= 3 and self._polygon_area(element.polygon) <= 0:
                issues.append(
                    GeometryValidationIssue(
                        code="DEGENERATE_GEOMETRY",
                        message="Polygon area is zero or negative.",
                        severity=Severity.medium,
                        element_id=element.id,
                    )
                )
        return issues

    def _polygon_area(self, polygon) -> float:
        area = 0.0
        for i in range(len(polygon)):
            j = (i + 1) % len(polygon)
            area += polygon[i].x * polygon[j].y
            area -= polygon[j].x * polygon[i].y
        return abs(area) / 2.0
