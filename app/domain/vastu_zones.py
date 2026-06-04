"""Vastu directional zones — deterministic domain constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VastuZone:
    """One compass sector with Sanskrit name and recommended uses."""

    key: str
    sanskrit: str
    element: str
    start_degrees: float
    end_degrees: float
    recommended_uses: tuple[str, ...]
    avoid_uses: tuple[str, ...] = ()


class VastuZoneCatalog:
    """
    Canonical 8-zone + Brahmasthan map.

    Compass bearings (True North = 0/360°, East = 90°, South = 180°, West = 270°).
    """

    BRAHMASTHAN = VastuZone(
        key="center",
        sanskrit="Brahmasthan",
        element="Space",
        start_degrees=0.0,
        end_degrees=360.0,
        recommended_uses=("open_courtyard", "light_well", "passage"),
        avoid_uses=("kitchen", "toilet", "staircase", "heavy_load", "pillar"),
    )

    ZONES: tuple[VastuZone, ...] = (
        VastuZone(
            key="north",
            sanskrit="Kubera",
            element="Water",
            start_degrees=337.5,
            end_degrees=22.5,
            recommended_uses=("living_room", "entrance", "treasury"),
        ),
        VastuZone(
            key="north_east",
            sanskrit="Ishan",
            element="Water / Prayer",
            start_degrees=22.5,
            end_degrees=67.5,
            recommended_uses=("pooja", "meditation", "entrance"),
            avoid_uses=("toilet", "kitchen", "staircase"),
        ),
        VastuZone(
            key="east",
            sanskrit="Indra",
            element="Air / Sun",
            start_degrees=67.5,
            end_degrees=112.5,
            recommended_uses=("living_room", "entrance", "study"),
        ),
        VastuZone(
            key="south_east",
            sanskrit="Agneya",
            element="Fire",
            start_degrees=112.5,
            end_degrees=157.5,
            recommended_uses=("kitchen", "electrical"),
            avoid_uses=("toilet", "bedroom"),
        ),
        VastuZone(
            key="south",
            sanskrit="Yama",
            element="Fire / Ancestors",
            start_degrees=157.5,
            end_degrees=202.5,
            recommended_uses=("storage", "heavy_equipment"),
        ),
        VastuZone(
            key="south_west",
            sanskrit="Nairutya",
            element="Earth",
            start_degrees=202.5,
            end_degrees=247.5,
            recommended_uses=("master_bedroom", "heavy_furniture"),
            avoid_uses=("entrance", "pooja"),
        ),
        VastuZone(
            key="west",
            sanskrit="Varuna",
            element="Water",
            start_degrees=247.5,
            end_degrees=292.5,
            recommended_uses=("children_bedroom", "study", "dining"),
        ),
        VastuZone(
            key="north_west",
            sanskrit="Vayu",
            element="Air",
            start_degrees=292.5,
            end_degrees=337.5,
            recommended_uses=("guest_room", "storage", "garage"),
        ),
    )

    @classmethod
    def resolve(cls, bearing_degrees: float) -> str:
        normalized = bearing_degrees % 360.0
        for zone in cls.ZONES:
            if zone.start_degrees > zone.end_degrees:
                if normalized >= zone.start_degrees or normalized < zone.end_degrees:
                    return zone.key
            elif zone.start_degrees <= normalized < zone.end_degrees:
                return zone.key
        return "north"

    @classmethod
    def get(cls, key: str) -> VastuZone | None:
        for zone in cls.ZONES:
            if zone.key == key:
                return zone
        if key == "center":
            return cls.BRAHMASTHAN
        return None

    @classmethod
    def to_api_list(cls) -> list[dict[str, str | float | list[str]]]:
        rows: list[dict[str, str | float | list[str]]] = []
        for zone in cls.ZONES:
            rows.append(
                {
                    "zone": zone.key,
                    "sanskrit": zone.sanskrit,
                    "element": zone.element,
                    "start_degrees": zone.start_degrees,
                    "end_degrees": zone.end_degrees,
                    "recommended_uses": list(zone.recommended_uses),
                    "avoid_uses": list(zone.avoid_uses),
                }
            )
        brahm = cls.BRAHMASTHAN
        rows.append(
            {
                "zone": brahm.key,
                "sanskrit": brahm.sanskrit,
                "element": brahm.element,
                "start_degrees": brahm.start_degrees,
                "end_degrees": brahm.end_degrees,
                "recommended_uses": list(brahm.recommended_uses),
                "avoid_uses": list(brahm.avoid_uses),
            }
        )
        return rows
