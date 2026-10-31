"""Geocoding providers (text -> coordinates) plus a small cached search helper."""
from __future__ import annotations

from typing import Protocol

import requests

from ..domain.types import Place
from ..errors import ConfigError, UpstreamError


class Geocoder(Protocol):
    name: str

    def search(self, query: str, limit: int = 5) -> list[Place]: ...


def _get_json(session, url: str, params: dict, what: str) -> dict:
    try:
        response = session.get(url, params=params, timeout=15)
    except requests.RequestException as exc:
        raise UpstreamError(f"{what} unreachable: {exc}") from exc
    if response.status_code in (401, 403):
        raise UpstreamError(f"{what} rejected the API key")
    if response.status_code != 200:
        raise UpstreamError(f"{what} error (HTTP {response.status_code})")
    try:
        return response.json()
    except ValueError as exc:
        raise UpstreamError(f"{what} returned invalid JSON") from exc


class MapboxGeocoder:
    name = "mapbox"
    URL = "https://api.mapbox.com/search/geocode/v6/forward"

    def __init__(self, access_token: str, country: str = "", session=None):
        if not access_token:
            raise ConfigError("MAPBOX_ACCESS_TOKEN is not set")
        self.token = access_token
        self.country = country
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 5) -> list[Place]:
        params = {"q": query, "limit": limit, "autocomplete": "true", "access_token": self.token}
        if self.country:
            params["country"] = self.country.lower()
        data = _get_json(self.session, self.URL, params, "Geocoding service")
        places = []
        for feature in data.get("features", []):
            lon, lat = feature["geometry"]["coordinates"][:2]
            props = feature.get("properties", {})
            label = props.get("full_address") or ", ".join(
                part for part in (props.get("name"), props.get("place_formatted")) if part
            )
            places.append(Place(lat=lat, lon=lon, label=label))
        return places


class OrsGeocoder:
    """OpenRouteService geocoding (Pelias)."""

    name = "ors"
    URL = "https://api.openrouteservice.org/geocode/autocomplete"

    def __init__(self, api_key: str, country: str = "", session=None):
        if not api_key:
            raise ConfigError("ORS_API_KEY is not set")
        self.api_key = api_key
        self.country = country
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 5) -> list[Place]:
        params = {"api_key": self.api_key, "text": query, "size": limit}
        if self.country:
            params["boundary.country"] = self.country.upper()
        data = _get_json(self.session, self.URL, params, "Geocoding service")
        places = []
        for feature in data.get("features", []):
            lon, lat = feature["geometry"]["coordinates"][:2]
            places.append(Place(lat=lat, lon=lon, label=feature.get("properties", {}).get("label", "")))
        return places


_MOCK_CITIES = {
    "Albuquerque, NM": (35.0844, -106.6504),
    "Atlanta, GA": (33.7490, -84.3880),
    "Chicago, IL": (41.8781, -87.6298),
    "Dallas, TX": (32.7767, -96.7970),
    "Denver, CO": (39.7392, -104.9903),
    "Houston, TX": (29.7604, -95.3698),
    "Kansas City, MO": (39.0997, -94.5786),
    "Los Angeles, CA": (34.0522, -118.2437),
    "Memphis, TN": (35.1495, -90.0490),
    "Minneapolis, MN": (44.9778, -93.2650),
    "Nashville, TN": (36.1627, -86.7816),
    "New York, NY": (40.7128, -74.0060),
    "Oklahoma City, OK": (35.4676, -97.5164),
    "Omaha, NE": (41.2565, -95.9345),
    "Phoenix, AZ": (33.4484, -112.0740),
    "Salt Lake City, UT": (40.7608, -111.8910),
    "Seattle, WA": (47.6062, -122.3321),
}


class MockGeocoder:
    """Offline geocoder over a handful of US cities."""

    name = "mock"

    def search(self, query: str, limit: int = 5) -> list[Place]:
        needle = query.strip().lower()
        matches = [
            Place(lat=lat, lon=lon, label=label)
            for label, (lat, lon) in _MOCK_CITIES.items()
            if needle in label.lower()
        ]
        return matches[:limit]


def cached_search(geocoder: Geocoder, query: str, limit: int = 5, ttl_seconds: int = 3600) -> list[Place]:
    """Search with a Django-cache layer so repeated keystrokes don't burn API quota."""
    from django.core.cache import cache

    key = f"geo:{geocoder.name}:{limit}:{query.strip().lower()}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    places = geocoder.search(query.strip(), limit)
    cache.set(key, places, ttl_seconds)
    return places
