"""Offline routing provider for development and tests (no network, no key).

Returns three deterministic routes between the two places: a direct one and two
bowed ones (north / south), each with a different average speed.
"""
from __future__ import annotations

import math

from ...domain.geometry import cumulative_miles
from ...domain.types import Place, RawRoute

POINTS_PER_ROUTE = 400
# (id, summary, bow as a fraction of trip length, average speed in mph)
_SHAPES = (
    ("r1", "Direct route (mock)", 0.0, 58.0),
    ("r2", "Northern route (mock)", 0.10, 55.0),
    ("r3", "Southern route (mock)", -0.10, 52.0),
)


class MockRoutingProvider:
    name = "mock"

    def get_routes(self, origin: Place, destination: Place) -> list[RawRoute]:
        dlat, dlon = destination.lat - origin.lat, destination.lon - origin.lon
        length_deg = math.hypot(dlat, dlon)
        if length_deg == 0:
            return [RawRoute("r1", "Direct route (mock)", [(origin.lat, origin.lon)] * 2, 60.0)]
        # unit vector perpendicular to the trip direction
        perp_lat, perp_lon = -dlon / length_deg, dlat / length_deg

        routes = []
        for route_id, summary, bow, speed_mph in _SHAPES:
            coords = []
            for i in range(POINTS_PER_ROUTE + 1):
                t = i / POINTS_PER_ROUTE
                offset = bow * length_deg * math.sin(math.pi * t)
                coords.append(
                    (
                        origin.lat + dlat * t + perp_lat * offset,
                        origin.lon + dlon * t + perp_lon * offset,
                    )
                )
            miles = cumulative_miles(coords)[-1] * 1.15  # roads wander
            routes.append(RawRoute(route_id, summary, coords, miles / speed_mph * 3600))
        return routes
