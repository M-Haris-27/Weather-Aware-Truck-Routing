"""Mapbox Directions: the primary route + up to 2 alternatives (3 routes total)."""
from __future__ import annotations

import requests

from ...domain.types import Place, RawRoute
from ...errors import ConfigError, NoRouteError, UpstreamError


class MapboxProvider:
    name = "mapbox"
    URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
    TIMEOUT_S = 30

    def __init__(self, access_token: str, session=None):
        if not access_token:
            raise ConfigError("MAPBOX_ACCESS_TOKEN is not set")
        self.token = access_token
        self.session = session or requests.Session()

    def get_routes(self, origin: Place, destination: Place) -> list[RawRoute]:
        url = self.URL.format(coords=f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}")
        params = {
            "access_token": self.token,
            "alternatives": "true",
            "geometries": "geojson",
            "overview": "full",
            "steps": "false",
        }
        try:
            response = self.session.get(url, params=params, timeout=self.TIMEOUT_S)
        except requests.RequestException as exc:
            raise UpstreamError(f"Routing service unreachable: {exc}") from exc

        if response.status_code in (401, 403):
            raise UpstreamError("Routing service rejected the API key")
        try:
            data = response.json()
        except ValueError as exc:
            raise UpstreamError(f"Routing service returned invalid JSON (HTTP {response.status_code})") from exc

        code = data.get("code")
        if code in ("NoRoute", "NoSegment"):
            raise NoRouteError("No drivable route found between those places")
        if response.status_code != 200 or code != "Ok":
            raise UpstreamError(f"Routing service error: {data.get('message', code or response.status_code)}")

        routes = []
        for i, item in enumerate(data.get("routes", [])[:3], start=1):
            coords = [(lat, lon) for lon, lat in item["geometry"]["coordinates"]]
            summary = (item.get("legs") or [{}])[0].get("summary") or f"Route {i}"
            routes.append(RawRoute(id=f"r{i}", summary=summary, coordinates=coords, duration_s=item["duration"]))
        if not routes:
            raise NoRouteError("No drivable route found between those places")
        return routes
