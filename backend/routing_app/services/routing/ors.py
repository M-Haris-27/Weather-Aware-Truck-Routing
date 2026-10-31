"""OpenRouteService with the truck (`driving-hgv`) profile.

Caveat: the public ORS API refuses alternative routes beyond roughly 100 km (error 2004).
When that happens we retry without alternatives, so long trips return a single route.
"""
from __future__ import annotations

import requests

from ...domain.types import Place, RawRoute
from ...errors import ConfigError, NoRouteError, UpstreamError

ALTERNATIVES_TOO_LONG = 2004
NO_ROUTE_CODES = {2009, 2010}  # route not found / no routable point nearby


class OrsProvider:
    name = "ors"
    URL = "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"
    TIMEOUT_S = 30

    def __init__(self, api_key: str, session=None):
        if not api_key:
            raise ConfigError("ORS_API_KEY is not set")
        self.api_key = api_key
        self.session = session or requests.Session()

    def get_routes(self, origin: Place, destination: Place) -> list[RawRoute]:
        body = {
            "coordinates": [[origin.lon, origin.lat], [destination.lon, destination.lat]],
            "instructions": False,
            "alternative_routes": {"target_count": 3, "weight_factor": 1.6, "share_factor": 0.6},
        }
        status, data = self._post(body)
        if self._error_code(data) == ALTERNATIVES_TOO_LONG:
            body.pop("alternative_routes")
            status, data = self._post(body)

        code = self._error_code(data)
        if code in NO_ROUTE_CODES:
            raise NoRouteError("No drivable route found between those places")
        if status != 200 or "features" not in data:
            message = (data.get("error") or {}).get("message") if isinstance(data.get("error"), dict) else None
            raise UpstreamError(f"Routing service error: {message or f'HTTP {status}'}")

        routes = []
        for i, feature in enumerate(data["features"][:3], start=1):
            coords = [(c[1], c[0]) for c in feature["geometry"]["coordinates"]]
            duration = feature["properties"]["summary"]["duration"]
            routes.append(RawRoute(id=f"r{i}", summary=f"Route {i}", coordinates=coords, duration_s=duration))
        if not routes:
            raise NoRouteError("No drivable route found between those places")
        return routes

    def _post(self, body: dict) -> tuple[int, dict]:
        try:
            response = self.session.post(
                self.URL,
                json=body,
                headers={"Authorization": self.api_key, "Content-Type": "application/json"},
                timeout=self.TIMEOUT_S,
            )
        except requests.RequestException as exc:
            raise UpstreamError(f"Routing service unreachable: {exc}") from exc
        try:
            return response.status_code, response.json()
        except ValueError as exc:
            raise UpstreamError(f"Routing service returned invalid JSON (HTTP {response.status_code})") from exc

    @staticmethod
    def _error_code(data: dict):
        error = data.get("error")
        return error.get("code") if isinstance(error, dict) else None
