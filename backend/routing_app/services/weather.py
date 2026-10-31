"""Weather providers.

A provider takes many points and one time window and returns an hourly forecast per
grid point, so the pipeline needs exactly one (batched) weather call per analysis.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Protocol

import requests

from ..domain.types import Coord, GridKey, HourlySeries, Weather, grid_key
from ..errors import UpstreamError

UTC = timezone.utc


class WeatherProvider(Protocol):
    def fetch(self, points: Iterable[Coord], start: datetime, end: datetime) -> dict[GridKey, HourlySeries]:
        """Hourly forecast per grid point covering at least [start, end] (UTC)."""


class OpenMeteoProvider:
    """Open-Meteo forecast API (no key). Batches coordinates and caches per grid point."""

    URL = "https://api.open-meteo.com/v1/forecast"
    HOURLY = "wind_speed_10m,rain,showers,snowfall"
    CHUNK_SIZE = 50
    MAX_WORKERS = 4
    TIMEOUT_S = 20
    RETRIES = 2
    RETRY_STATUS = (429, 500, 502, 503, 504)

    def __init__(self, session=None, cache=None, ttl_seconds: int = 1800):
        self.session = session or requests.Session()
        if cache is None:
            from django.core.cache import cache as django_cache

            cache = django_cache
        self.cache = cache
        self.ttl = ttl_seconds

    # -- public ---------------------------------------------------------------
    def fetch(self, points, start, end):
        start_date = start.astimezone(UTC).date()
        end_date = end.astimezone(UTC).date()

        keys = list(dict.fromkeys(grid_key(lat, lon) for lat, lon in points))
        result: dict[GridKey, HourlySeries] = {}
        missing: list[GridKey] = []
        for key in keys:
            cached = self.cache.get(self._cache_key(key, start_date, end_date))
            if cached is not None:
                result[key] = cached
            else:
                missing.append(key)

        chunks = [missing[i : i + self.CHUNK_SIZE] for i in range(0, len(missing), self.CHUNK_SIZE)]
        if chunks:
            with ThreadPoolExecutor(max_workers=min(self.MAX_WORKERS, len(chunks))) as pool:
                fetched = pool.map(lambda chunk: self._fetch_chunk(chunk, start_date, end_date), chunks)
                for chunk, series_list in zip(chunks, fetched):
                    for key, series in zip(chunk, series_list):
                        result[key] = series
                        self.cache.set(self._cache_key(key, start_date, end_date), series, self.ttl)
        return result

    # -- internals ------------------------------------------------------------
    @staticmethod
    def _cache_key(key: GridKey, start_date: date, end_date: date) -> str:
        return f"wx:{key[0]:.2f}:{key[1]:.2f}:{start_date}:{end_date}"

    def _fetch_chunk(self, chunk: list[GridKey], start_date: date, end_date: date) -> list[HourlySeries]:
        params = {
            "latitude": ",".join(f"{lat:.2f}" for lat, _ in chunk),
            "longitude": ",".join(f"{lon:.2f}" for _, lon in chunk),
            "hourly": self.HOURLY,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        last_problem = "no response"
        for attempt in range(self.RETRIES + 1):
            try:
                response = self.session.get(self.URL, params=params, timeout=self.TIMEOUT_S)
            except requests.RequestException as exc:
                last_problem = str(exc)
                time.sleep(0.5 * (attempt + 1))
                continue
            if response.status_code in self.RETRY_STATUS:
                last_problem = f"HTTP {response.status_code}"
                time.sleep(0.5 * (attempt + 1))
                continue
            if response.status_code != 200:
                raise UpstreamError(f"Weather service error: {self._reason(response)}")
            return self._parse(response.json(), len(chunk))
        raise UpstreamError(f"Weather service unavailable ({last_problem})")

    @staticmethod
    def _reason(response) -> str:
        try:
            return response.json().get("reason", f"HTTP {response.status_code}")
        except ValueError:
            return f"HTTP {response.status_code}"

    @classmethod
    def _parse(cls, payload, expected: int) -> list[HourlySeries]:
        # One location -> a single object; several -> a list in request order.
        items = payload if isinstance(payload, list) else [payload]
        if len(items) != expected:
            raise UpstreamError("Weather service returned an unexpected number of locations")
        try:
            return [cls._series(item["hourly"]) for item in items]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise UpstreamError(f"Weather service returned malformed data ({exc!r})") from exc

    @staticmethod
    def _series(hourly: dict) -> HourlySeries:
        times = hourly["time"]
        start = datetime.fromisoformat(times[0]).replace(tzinfo=UTC)  # timezone=GMT
        values = []
        for i in range(len(times)):
            wind = hourly["wind_speed_10m"][i] or 0.0
            rain = (hourly["rain"][i] or 0.0) + (hourly["showers"][i] or 0.0)
            snow = hourly["snowfall"][i] or 0.0
            values.append(Weather(float(wind), round(float(rain), 3), round(float(snow), 3)))
        return HourlySeries(start=start, values=tuple(values))


def default_synthetic_weather(lat: float, lon: float, when: datetime) -> Weather:
    """Deterministic, varied fake weather: storms that drift with time and position."""
    hours = when.timestamp() / 3600
    phase = math.radians(lat * 7 + lon * 5) + hours / 9
    wind = 14 + 26 * max(0.0, math.sin(phase)) ** 2
    rain = 0.35 * max(0.0, math.sin(phase * 0.7 + 1.3)) ** 3
    snow = 0.8 * max(0.0, math.sin(phase * 0.5 + 2.0)) ** 3 if lat > 40 else 0.0
    return Weather(round(wind, 1), round(rain, 2), round(snow, 2))


class SyntheticWeatherProvider:
    """Offline provider for development and tests. Pass `fn(lat, lon, hour_dt)` to script it."""

    def __init__(self, fn: Callable[[float, float, datetime], Weather] | None = None):
        self.fn = fn or default_synthetic_weather

    def fetch(self, points, start, end):
        first = datetime.combine(start.astimezone(UTC).date(), dtime(0), tzinfo=UTC)
        last = datetime.combine(end.astimezone(UTC).date(), dtime(23), tzinfo=UTC)
        hours = [first + timedelta(hours=h) for h in range(int((last - first).total_seconds() // 3600) + 1)]
        result: dict[GridKey, HourlySeries] = {}
        for lat, lon in points:
            key = grid_key(lat, lon)
            if key not in result:
                result[key] = HourlySeries(
                    start=first, values=tuple(self.fn(key[0], key[1], hour) for hour in hours)
                )
        return result
