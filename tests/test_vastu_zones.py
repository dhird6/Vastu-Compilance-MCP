import pytest

from app.domain.vastu_zones import VastuZoneCatalog
from app.services.geometry.shapely_ops import bearing_from_center
from app.models.schemas import Point2D


def test_north_bearing_from_center():
    center = Point2D(x=0, y=0)
    north_room = Point2D(x=0, y=10)
    bearing = bearing_from_center(north_room, center, true_north_degrees=0)
    assert VastuZoneCatalog.resolve(bearing) == "north"


def test_east_bearing_from_center():
    center = Point2D(x=0, y=0)
    east_room = Point2D(x=10, y=0)
    bearing = bearing_from_center(east_room, center, true_north_degrees=0)
    assert VastuZoneCatalog.resolve(bearing) == "east"


def test_south_east_kitchen_zone():
    center = Point2D(x=0, y=0)
    se_room = Point2D(x=10, y=-10)
    bearing = bearing_from_center(se_room, center, true_north_degrees=0)
    zone = VastuZoneCatalog.resolve(bearing)
    assert zone in {"south_east", "south", "east"}


def test_ishan_zone_metadata():
    zone = VastuZoneCatalog.get("north_east")
    assert zone is not None
    assert zone.sanskrit == "Ishan"
    assert "pooja" in zone.recommended_uses


def test_directional_zones_api_list_includes_brahmasthan():
    rows = VastuZoneCatalog.to_api_list()
    keys = {row["zone"] for row in rows}
    assert "center" in keys
    assert "north_east" in keys
