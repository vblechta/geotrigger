from __future__ import annotations

from math import asin, cos, radians, sin, sqrt


EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two WGS84 points."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def is_inside(lat: float, lon: float, location_lat: float, location_lon: float, radius_m: float) -> bool:
    return haversine_m(lat, lon, location_lat, location_lon) <= radius_m
