from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.domain.vastu_zones import VastuZoneCatalog
from app.models.schemas import RoomOrientation, RuleEvaluationResult, Severity


class RuleRegistry:
    """Versioned rule catalog — deterministic evaluation only."""

    def __init__(self, rules_path: Path) -> None:
        self.rules_path = rules_path
        self._document = self._load(rules_path)

    @property
    def version(self) -> str:
        return str(self._document.get("version", "1"))

    @property
    def rules(self) -> list[dict[str, Any]]:
        return list(self._document.get("rules", []))

    def list_rules(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "description": self._document.get("description", ""),
            "rules": self.rules,
        }

    def _load(self, rules_path: Path) -> dict[str, Any]:
        suffix = rules_path.suffix.lower()
        with rules_path.open("r", encoding="utf-8") as file:
            if suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(file)
            elif suffix == ".json":
                data = json.load(file)
            else:
                raise ValueError(f"Unsupported rules format: {rules_path.suffix}")
        return data or {}


class VastuRuleEngine:
    def __init__(self, rules_path: Path) -> None:
        self.registry = RuleRegistry(rules_path)
        self.rules_path = rules_path

    @property
    def rules(self) -> dict[str, Any]:
        return self.registry._document

    def evaluate(self, room_orientations: list[RoomOrientation]) -> list[RuleEvaluationResult]:
        by_type = {
            rule["room_type"].strip().lower(): rule
            for rule in self.registry.rules
        }
        results: list[RuleEvaluationResult] = []

        for room in room_orientations:
            rule = by_type.get(room.room_type)
            if not rule:
                continue
            results.append(self._evaluate_room(room, rule))

            brahm = self._evaluate_brahmasthan(room)
            if brahm is not None:
                results.append(brahm)

        return results

    def evaluate_room(self, room: RoomOrientation) -> list[RuleEvaluationResult]:
        """Stateless single-room rule check for MCP thin tools."""
        by_type = {
            rule["room_type"].strip().lower(): rule
            for rule in self.registry.rules
        }
        results: list[RuleEvaluationResult] = []
        rule = by_type.get(room.room_type)
        if rule:
            results.append(self._evaluate_room(room, rule))
        brahm = self._evaluate_brahmasthan(room)
        if brahm is not None:
            results.append(brahm)
        return results

    def _evaluate_room(self, room: RoomOrientation, rule: dict[str, Any]) -> RuleEvaluationResult:
        preferred = [z.strip().lower() for z in rule.get("preferred_zones", [])]
        avoided = [z.strip().lower() for z in rule.get("avoid_zones", [])]
        min_area = float(rule.get("min_area", 0.0))
        severity = Severity(rule.get("severity", "medium"))
        score_impact = float(rule.get("score_impact", 5.0))

        zone_compliant = room.zone in preferred if preferred else True
        zone_violated = room.zone in avoided if avoided else False
        area_compliant = room.area >= min_area

        passed = zone_compliant and not zone_violated and area_compliant
        explanation = self._build_explanation(
            room_type=room.room_type,
            zone=room.zone,
            preferred=preferred,
            avoided=avoided,
            min_area=min_area,
            area=room.area,
            passed=passed,
        )
        confidence = 0.93 if passed else 0.88

        return RuleEvaluationResult(
            rule_id=rule["id"],
            title=rule["title"],
            passed=passed,
            room_id=room.room_id,
            zone=room.zone,
            expected_zones=preferred,
            avoided_zones=avoided,
            severity=severity,
            score_impact=score_impact if not passed else 0.0,
            confidence=confidence,
            explanation=explanation,
        )

    def _evaluate_brahmasthan(self, room: RoomOrientation) -> RuleEvaluationResult | None:
        in_brahm = bool(room.metadata.get("in_brahmasthan", False))
        if not in_brahm:
            return None

        heavy_types = {"kitchen", "toilet", "staircase", "storage"}
        if room.room_type not in heavy_types:
            return None

        zone_meta = VastuZoneCatalog.BRAHMASTHAN
        passed = False
        return RuleEvaluationResult(
            rule_id="VR-BRAHM",
            title="Heavy room overlaps Brahmasthan (center)",
            passed=passed,
            room_id=room.room_id,
            zone="center",
            expected_zones=list(zone_meta.recommended_uses),
            avoided_zones=list(zone_meta.avoid_uses),
            severity=Severity.high,
            score_impact=12.0,
            confidence=0.90,
            explanation=(
                f"{room.room_type} centroid lies in Brahmasthan (center zone). "
                "Keep center open — no kitchen, toilet, staircase, or heavy loads."
            ),
        )

    def _build_explanation(
        self,
        room_type: str,
        zone: str,
        preferred: list[str],
        avoided: list[str],
        min_area: float,
        area: float,
        passed: bool,
    ) -> str:
        preferred_text = ", ".join(preferred) if preferred else "any zone"
        avoided_text = ", ".join(avoided) if avoided else "none"
        zone_meta = VastuZoneCatalog.get(zone)
        sanskrit = f" ({zone_meta.sanskrit})" if zone_meta else ""
        if passed:
            return (
                f"{room_type} complies: located in {zone}{sanskrit}, preferred zones {preferred_text}, "
                f"avoided zones {avoided_text}, and area {area:.2f} >= {min_area:.2f}."
            )
        return (
            f"{room_type} is non-compliant: current zone {zone}{sanskrit}, preferred zones {preferred_text}, "
            f"avoided zones {avoided_text}, and area {area:.2f} vs minimum {min_area:.2f}."
        )
