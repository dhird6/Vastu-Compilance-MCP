from __future__ import annotations

from app.domain.vastu_zones import VastuZoneCatalog


class DirectionEngine:
    """Resolves compass bearings to Vastu zones using deterministic catalog."""

    def resolve_zone(self, angle_degrees: float) -> str:
        return VastuZoneCatalog.resolve(angle_degrees)

    def build_directional_zones(self) -> list[dict[str, float | str | list[str]]]:
        return VastuZoneCatalog.to_api_list()

    def zone_metadata(self, zone_key: str) -> dict[str, str | list[str]] | None:
        zone = VastuZoneCatalog.get(zone_key)
        if zone is None:
            return None
        return {
            "zone": zone.key,
            "sanskrit": zone.sanskrit,
            "element": zone.element,
            "recommended_uses": list(zone.recommended_uses),
            "avoid_uses": list(zone.avoid_uses),
        }
