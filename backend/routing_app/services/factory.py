"""Builds the configured providers from Django settings."""
from __future__ import annotations

from django.conf import settings

from ..errors import ConfigError
from .geocoding import Geocoder, MapboxGeocoder, MockGeocoder, OrsGeocoder
from .routing import MapboxProvider, MockRoutingProvider, OrsProvider, RoutingProvider
from .weather import OpenMeteoProvider, SyntheticWeatherProvider, WeatherProvider


def get_routing_provider() -> RoutingProvider:
    name = settings.ROUTING_PROVIDER
    if name == "mapbox":
        return MapboxProvider(settings.MAPBOX_ACCESS_TOKEN)
    if name == "ors":
        return OrsProvider(settings.ORS_API_KEY)
    if name == "mock":
        return MockRoutingProvider()
    raise ConfigError(f"Unknown ROUTING_PROVIDER '{name}' (use mapbox, ors or mock)")


def get_geocoder() -> Geocoder:
    name = settings.GEOCODING_PROVIDER
    if name == "mapbox":
        return MapboxGeocoder(settings.MAPBOX_ACCESS_TOKEN, settings.GEOCODING_COUNTRY)
    if name == "ors":
        return OrsGeocoder(settings.ORS_API_KEY, settings.GEOCODING_COUNTRY)
    if name == "mock":
        return MockGeocoder()
    raise ConfigError(f"Unknown GEOCODING_PROVIDER '{name}' (use mapbox, ors or mock)")


def get_weather_provider() -> WeatherProvider:
    name = settings.WEATHER_PROVIDER
    if name == "open_meteo":
        return OpenMeteoProvider(ttl_seconds=settings.WEATHER_CACHE_TTL_SECONDS)
    if name == "mock":
        return SyntheticWeatherProvider()
    raise ConfigError(f"Unknown WEATHER_PROVIDER '{name}' (use open_meteo or mock)")
