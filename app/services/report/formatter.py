from __future__ import annotations

from app.domain.vastu_zones import VastuZoneCatalog
from app.models.schemas import ComplianceReport, RoomOrientation, RuleEvaluationResult


class ReportFormatter:
    """Builds structured executive output for Revit UI and HTML export."""

    def build(self, report: ComplianceReport) -> dict:
        room_map = {room.room_id: room for room in report.orientations}
        failures = [r for r in report.rule_results if not r.passed]
        passes = [r for r in report.rule_results if r.passed]

        room_dashboard = self._build_room_dashboard(report.orientations, report.rule_results, report.heatmap)
        zone_legend = VastuZoneCatalog.to_api_list()
        priority_fixes = self._build_priority_fixes(failures, room_map, report)

        return {
            "executive_summary": {
                "headline": self._headline(report.summary.compliance_score, report.summary.grade),
                "compliance_score": report.summary.compliance_score,
                "grade": report.summary.grade,
                "total_rooms": report.summary.total_rooms,
                "passed_rules": report.summary.passed_rules,
                "failed_rules": report.summary.failed_rules,
                "violation_count": len(failures),
                "auto_fixes": report.remediation_plan.auto_applicable_count,
                "manual_fixes": report.remediation_plan.manual_approval_count,
                "request_id": report.request_id,
                "generated_at": report.generated_at.isoformat(),
            },
            "room_dashboard": room_dashboard,
            "priority_fixes": priority_fixes,
            "zone_legend": zone_legend,
            "compass": {
                "true_north_note": "Zones use centroid bearing + project True North",
                "sectors": len(zone_legend),
            },
            "remediation_summary": report.remediation_plan.summary,
            "validation_issue_count": len(report.validation_issues),
        }

    def _headline(self, score: float, grade: str) -> str:
        if score >= 85:
            return f"Excellent Vastu alignment (Grade {grade})"
        if score >= 70:
            return f"Good layout with minor adjustments needed (Grade {grade})"
        if score >= 50:
            return f"Moderate compliance — remediation recommended (Grade {grade})"
        return f"Significant Vastu violations — review ghost preview (Grade {grade})"

    def _build_room_dashboard(
        self,
        orientations: list[RoomOrientation],
        rule_results: list[RuleEvaluationResult],
        heatmap: list,
    ) -> list[dict]:
        by_room: dict[str, RuleEvaluationResult] = {}
        for result in rule_results:
            if result.room_id not in by_room or not result.passed:
                by_room[result.room_id] = result

        heat_by_room = {cell.room_id: cell for cell in heatmap}
        rows: list[dict] = []

        for room in orientations:
            result = by_room.get(room.room_id)
            heat = heat_by_room.get(room.room_id)
            zone_meta = VastuZoneCatalog.get(room.zone)
            target = result.expected_zones[0] if result and result.expected_zones else None
            target_meta = VastuZoneCatalog.get(target) if target else None

            rows.append(
                {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "room_type": room.room_type,
                    "zone": room.zone,
                    "zone_sanskrit": zone_meta.sanskrit if zone_meta else room.zone,
                    "zone_element": zone_meta.element if zone_meta else "",
                    "target_zone": target,
                    "target_sanskrit": target_meta.sanskrit if target_meta else None,
                    "area_sqft": round(room.area, 2),
                    "bearing_degrees": round(room.orientation_degrees, 1),
                    "status": heat.status if heat else ("compliant" if result and result.passed else "unknown"),
                    "color_hex": heat.color_hex if heat else "#9ACD32",
                    "rule_id": result.rule_id if result else None,
                    "rule_title": result.title if result else None,
                    "passed": result.passed if result else True,
                    "explanation": result.explanation if result else "No rule mapped",
                    "in_brahmasthan": bool(room.metadata.get("in_brahmasthan", False)),
                }
            )

        status_order = {"critical": 0, "warning": 1, "compliant": 2, "unknown": 3}
        rows.sort(key=lambda row: (status_order.get(row["status"], 9), row["room_name"]))
        return rows

    def _build_priority_fixes(
        self,
        failures: list[RuleEvaluationResult],
        room_map: dict[str, RoomOrientation],
        report: ComplianceReport,
    ) -> list[dict]:
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_failures = sorted(
            failures,
            key=lambda item: (severity_rank.get(item.severity.value, 9), -item.score_impact),
        )
        rec_map = {rec.room_id: rec for rec in report.recommendations}
        fixes: list[dict] = []

        for result in sorted_failures[:12]:
            room = room_map.get(result.room_id)
            rec = rec_map.get(result.room_id)
            target = result.expected_zones[0] if result.expected_zones else ""
            target_meta = VastuZoneCatalog.get(target)

            fixes.append(
                {
                    "priority": len(fixes) + 1,
                    "room_name": room.room_name if room else result.room_id,
                    "room_type": room.room_type if room else "",
                    "rule_id": result.rule_id,
                    "severity": result.severity.value,
                    "current_zone": result.zone,
                    "target_zone": target,
                    "target_sanskrit": target_meta.sanskrit if target_meta else target,
                    "score_impact": result.score_impact,
                    "recommendation": rec.recommendation if rec else result.explanation,
                    "scriptural_ref": rec.scriptural_references[0] if rec and rec.scriptural_references else None,
                }
            )

        return fixes
