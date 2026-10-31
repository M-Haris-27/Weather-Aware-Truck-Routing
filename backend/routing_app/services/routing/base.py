from __future__ import annotations

from typing import Protocol

from ...domain.types import Place, RawRoute

METERS_PER_MILE = 1609.344


class RoutingProvider(Protocol):
    name: str

    def get_routes(self, origin: Place, destination: Place) -> list[RawRoute]:
        """Up to three alternative routes, best first. Raise NoRouteError if none exist."""
